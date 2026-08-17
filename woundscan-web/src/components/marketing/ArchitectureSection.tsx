import { Reveal } from "./Reveal";

/**
 * Animated AWS architecture diagram — the POC pipeline from the SOW:
 * iPhone → API Gateway/Lambda → processing pipeline → SageMaker (SAM) +
 * Bedrock → encrypted storage → provider portal. Pure SVG, token-colored,
 * flow lines animated via the .mk-flow dash keyframes.
 */
export function ArchitectureSection() {
  return (
    <section id="platform" className="relative scroll-mt-20 py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <span className="eyebrow">Platform</span>
          <h2 className="mk-h2 mt-3">
            An end-to-end pipeline, <span className="text-gradient">born on AWS.</span>
          </h2>
          <p className="mk-lead">
            Designed and validated with AWS partner engineering: serverless ingestion, an automated
            processing pipeline, managed AI services for segmentation and narration, and encrypted,
            lifecycle-managed storage — the same architecture that carries forward into production.
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="mk-card mt-12 overflow-x-auto !p-4 md:!p-8">
            <svg viewBox="0 0 960 380" className="w-full min-w-[760px]" role="img" aria-label="System architecture: iPhone capture app connects through API Gateway and Lambda to a processing pipeline using SageMaker and Bedrock, storing results in encrypted S3 and DynamoDB, surfaced in the provider portal">
              {/* Flow lines */}
              <g stroke="rgb(var(--accent) / 0.6)" strokeWidth="1.6" fill="none">
                <path className="mk-flow" d="M150 190 H 240" />
                <path className="mk-flow" d="M400 190 H 490" />
                <path className="mk-flow" d="M650 140 C 675 140, 675 100, 700 100" />
                <path className="mk-flow" d="M650 240 C 675 240, 675 280, 700 280" />
                <path className="mk-flow" d="M570 240 V 300 C 570 330, 620 330, 730 330" transform="translate(0,-140)" opacity="0" />
              </g>
              {/* Return line to portal */}
              <path className="mk-flow" d="M855 190 H 890" stroke="rgb(var(--gold) / 0.8)" strokeWidth="1.6" fill="none" />

              {/* iPhone node */}
              <ArchNode x={40} y={130} w={110} h={120} title="iOS capture" sub="ARKit · LiDAR" kind="edge" />
              {/* API layer */}
              <ArchNode x={240} y={130} w={160} h={120} title="API Gateway" sub="Lambda · signed uploads" kind="aws" />
              {/* Pipeline */}
              <ArchNode x={490} y={110} w={160} h={160} title="Processing pipeline" sub="preprocess · segment · measure · render · narrate" kind="aws" />
              {/* SageMaker */}
              <ArchNode x={700} y={50} w={150} h={90} title="SageMaker" sub="SAM boundary detection" kind="ai" />
              {/* Bedrock */}
              <ArchNode x={700} y={230} w={150} h={90} title="Bedrock" sub="guardrailed narration" kind="ai" />

              {/* Storage strip */}
              <g>
                <rect x="240" y="300" width="410" height="56" rx="10" fill="rgb(var(--surface-2))" stroke="rgb(var(--hairline))" />
                <text x="262" y="323" fontSize="12" fontFamily="var(--font-display), sans-serif" fontWeight="600" fill="rgb(var(--ink))">
                  Encrypted storage
                </text>
                <text x="262" y="341" fontSize="10.5" fontFamily="var(--font-mono), monospace" fill="rgb(var(--ink-muted))">
                  S3 (object lock) · DynamoDB · KMS keys · CloudWatch
                </text>
                <path className="mk-flow" d="M570 270 V 300" stroke="rgb(var(--accent) / 0.6)" strokeWidth="1.6" fill="none" />
              </g>

              {/* Portal node */}
              <g>
                <rect x="890" y="130" width="60" height="120" rx="10" fill="rgb(var(--accent) / 0.08)" stroke="rgb(var(--accent) / 0.5)" />
                <text x="920" y="185" fontSize="11" fontFamily="var(--font-display), sans-serif" fontWeight="600" fill="rgb(var(--ink))" textAnchor="middle" transform="rotate(-90 920 190)">
                  Provider portal
                </text>
              </g>
            </svg>

            <div className="mt-6 grid gap-3 border-t border-hairline pt-6 text-center sm:grid-cols-3">
              <ArchFact k="Serverless ingest" v="scales with scan volume, no idle cost" />
              <ArchFact k="Managed AI services" v="segmentation + narration with guardrails" />
              <ArchFact k="Encryption everywhere" v="KMS-managed keys, TLS in transit" />
            </div>
          </div>
        </Reveal>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {[
            {
              t: "iOS capture app",
              d: "SwiftUI + ARKit guided capture with live feedback, probe auto-detect, boundary annotation with ML proposal, and a 15-minute idle session timeout.",
            },
            {
              t: "Measurement engine",
              d: "Python FastAPI service — 13 subpackages covering capture, fusion, geometry, quality, ML, storage, and output — with an async worker for heavy fusion jobs.",
            },
            {
              t: "Provider portal",
              d: "The Next.js dashboard behind this site: TOTP MFA sign-in, wound trajectory charts, phantom calibration, admin and audit tooling, hardened security headers.",
            },
          ].map((c, i) => (
            <Reveal key={c.t} delay={i * 100}>
              <article className="mk-card h-full">
                <h3 className="font-display text-base font-semibold text-ink">{c.t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{c.d}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function ArchNode({
  x,
  y,
  w,
  h,
  title,
  sub,
  kind,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  sub: string;
  kind: "edge" | "aws" | "ai";
}) {
  const stroke =
    kind === "ai" ? "rgb(var(--gold) / 0.55)" : kind === "aws" ? "rgb(var(--accent) / 0.5)" : "rgb(var(--hairline))";
  const fill =
    kind === "ai" ? "rgb(var(--gold) / 0.06)" : kind === "aws" ? "rgb(var(--accent) / 0.06)" : "rgb(var(--surface-2))";
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="10" fill={fill} stroke={stroke} strokeWidth="1.3" />
      <text
        x={x + 16}
        y={y + 28}
        fontSize="13"
        fontFamily="var(--font-display), sans-serif"
        fontWeight="600"
        fill="rgb(var(--ink))"
      >
        {title}
      </text>
      {sub.split(" · ").map((line, i) => (
        <text key={line} x={x + 16} y={y + 48 + i * 15} fontSize="10.5" fontFamily="var(--font-mono), monospace" fill="rgb(var(--ink-muted))">
          {line}
        </text>
      ))}
    </g>
  );
}

function ArchFact({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <p className="font-display text-sm font-semibold text-ink">{k}</p>
      <p className="mt-0.5 text-xs text-ink-muted">{v}</p>
    </div>
  );
}
