"""Plain-language narration of measurements via Amazon Bedrock.

Flow per attempt: Converse (no guardrail on the request: the system prompt itself
lists forbidden topics and would trip the input filter) -> clean -> local checks
(>= 50 words, every value present, no clinical vocabulary) -> ApplyGuardrail on
the OUTPUT. The first attempt that passes everything wins.
"""

import json
import logging
import os
import re

import boto3
from botocore.config import Config

log = logging.getLogger(__name__)

DEFAULT_MODELS = "openai.gpt-oss-120b-1:0,us.meta.llama3-3-70b-instruct-v1:0"
ATTEMPTS_PER_MODEL = 2
MIN_WORDS = 50

SYSTEM_PROMPT = (
    "You write a plain-language summary of objective wound measurement data from a 3D LiDAR scan. "
    "Report ONLY the measured values and what each measurement represents. Write 70-110 words in one "
    "paragraph of plain text (no markdown, no lists, no headings). Mention every value with its unit "
    "exactly as given. Do NOT diagnose, name conditions, classify or stage the wound, assess severity "
    "or healing, predict outcomes, compare to normal ranges, or suggest any treatment, dressing or care. "
    "Output only the paragraph."
)

DEFINITIONS = (
    "Definitions: length and width are measured on the 3D point cloud along the longest axis and "
    "perpendicular to it; bed area is the area inside the actual wound boundary; depth is the distance "
    "from a reference plane fitted to the surrounding skin down to the deepest point; peri-wound area "
    "is a 20 mm ring of skin around the boundary."
)

BANNED = re.compile(
    r"\b(diagnos\w*|ulcer\w*|infect\w*|stage|stages|staging|staged|grade[sd]?|grading|severe|severity|"
    r"mild|moderate|heal\w*|treat\w*|dressing\w*|debrid\w*|antibiot\w*|necro\w*|recommend\w*|should|"
    r"prognos\w*|risk\w*|assess\w*|clinical\w*|concern\w*|abnormal|normal|improv\w*|worsen\w*|"
    r"condition\w*|care)\b",
    re.IGNORECASE,
)

FIELDS = [
    ("length_mm", "Length", "mm"),
    ("width_mm", "Width", "mm"),
    ("bed_area_cm2", "Wound bed area", "cm²"),
    ("depth_mm", "Depth", "mm"),
    ("peri_wound_area_cm2", "Peri-wound area (20 mm ring)", "cm²"),
]

_br = None


def _bedrock():
    global _br
    if _br is None:
        _br = boto3.client("bedrock-runtime", config=Config(read_timeout=60, retries={"max_attempts": 3, "mode": "standard"}))
    return _br


def fmt(v):
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def user_prompt(m):
    lines = [f"- {label}: {fmt(m[k])} {unit}" for k, label, unit in FIELDS]
    return "Measurements:\n" + "\n".join(lines) + "\n" + DEFINITIONS


def clean(text):
    t = text.replace("**", "").replace("__", "")
    t = re.sub(r"^\s*#+\s*", "", t, flags=re.MULTILINE)
    for a, b in {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": " - ",
                 " ": " ", " ": " ", " ": " ", "’": "'", "“": '"', "”": '"'}.items():
        t = t.replace(a, b)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", " ", t).strip()
    return t


def check(text, m):
    """Local acceptance checks. Returns a list of problems (empty = OK)."""
    problems = []
    words = len(re.findall(r"\b[\w.]+\b", text))
    if words < MIN_WORDS:
        problems.append(f"only {words} words")
    for k, _, _ in FIELDS:
        if fmt(m[k]) not in text:
            problems.append(f"missing value {k}={fmt(m[k])}")
    hit = BANNED.search(text)
    if hit:
        problems.append(f"clinical term '{hit.group(0)}'")
    return problems


def guardrail_ok(text):
    gid = os.environ.get("BEDROCK_GUARDRAIL_ID")
    ver = os.environ.get("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    if not gid:
        return True, "no guardrail configured"
    r = _bedrock().apply_guardrail(
        guardrailIdentifier=gid, guardrailVersion=ver, source="OUTPUT",
        content=[{"text": {"text": text}}],
    )
    if r.get("action") == "GUARDRAIL_INTERVENED":
        topics = [t.get("name") for a in r.get("assessments", [])
                  for t in a.get("topicPolicy", {}).get("topics", [])]
        return False, f"guardrail intervened {topics}"
    return True, "pass"


def generate(model_id, m):
    r = _bedrock().converse(
        modelId=model_id,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_prompt(m)}]}],
        inferenceConfig={"maxTokens": 1500, "temperature": 0.3},
    )
    blocks = r["output"]["message"]["content"]
    return "".join(b["text"] for b in blocks if "text" in b)   # skip reasoningContent blocks


def template(m):
    """Deterministic last-resort narration (used only if every model attempt fails)."""
    return (
        f"This summary lists the objective measurements taken from a 3D LiDAR scan. "
        f"The wound outline measures {fmt(m['length_mm'])} mm in length along its longest axis and "
        f"{fmt(m['width_mm'])} mm in width perpendicular to that axis, both taken from the 3D point cloud. "
        f"The wound bed area inside the traced boundary is {fmt(m['bed_area_cm2'])} cm². "
        f"The depth, measured from a reference plane fitted to the surrounding skin to the deepest point, "
        f"is {fmt(m['depth_mm'])} mm. The peri-wound area, a 20 mm ring of skin around the boundary, "
        f"is {fmt(m['peri_wound_area_cm2'])} cm²."
    )


def narrate(m):
    """Return (text, info dict)."""
    models = [x.strip() for x in os.environ.get("NARRATE_MODEL_IDS", DEFAULT_MODELS).split(",") if x.strip()]
    attempts = []
    for model_id in models:
        for i in range(ATTEMPTS_PER_MODEL):
            try:
                text = clean(generate(model_id, m))
            except Exception as e:  # model unavailable, throttled, etc.
                attempts.append({"model": model_id, "error": f"{type(e).__name__}: {e}"[:300]})
                log.warning("narration model %s failed: %s", model_id, e)
                break
            problems = check(text, m)
            if not problems:
                ok, why = guardrail_ok(text)
                if not ok:
                    problems.append(why)
            attempts.append({"model": model_id, "problems": problems, "words": len(text.split())})
            if not problems:
                return text, {"source": "bedrock", "model": model_id, "attempts": attempts}
            log.info("narration attempt rejected (%s): %s", model_id, problems)
    text = template(m)
    ok, why = guardrail_ok(text)
    info = {"source": "template", "model": None, "attempts": attempts, "template_guardrail": why}
    if not ok:
        raise RuntimeError("Narration failed: every model attempt and the template were rejected: "
                           + json.dumps(attempts)[:800])
    return text, info
