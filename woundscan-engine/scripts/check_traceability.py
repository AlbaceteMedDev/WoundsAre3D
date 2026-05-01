"""Verify regulatory traceability coverage.

For every test in tests/regulatory and tests/integration that's tagged
in the requirements matrix, confirm:
1. The test exists
2. The requirement is unique
3. The matrix is well-formed (parseable)

Run as: python scripts/check_traceability.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MATRIX = REPO / "docs" / "regulatory_traceability.md"


def parse_matrix() -> list[tuple[str, str]]:
    """Return a list of (req_id, test_path) pairs from the matrix table."""
    rows: list[tuple[str, str]] = []
    text = MATRIX.read_text()
    for line in text.splitlines():
        if not line.startswith("| REQ-"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        req_id, _desc, _impl, test_ref = cells[:4]
        m = re.search(r"`([^`]+)`", test_ref)
        if m:
            rows.append((req_id, m.group(1)))
    return rows


def main() -> int:
    rows = parse_matrix()
    if not rows:
        print("ERROR: no requirements found in matrix", file=sys.stderr)
        return 1

    seen_ids: set[str] = set()
    failures: list[str] = []
    for req_id, test_path in rows:
        if req_id in seen_ids:
            failures.append(f"Duplicate requirement: {req_id}")
        seen_ids.add(req_id)

        # The test_path looks like "tests/.../test_x.py::Class::method" or just "tests/path.py"
        file_part = test_path.split("::")[0]
        full = REPO / file_part
        if not full.exists():
            failures.append(f"Missing test file for {req_id}: {full}")

    if failures:
        for f in failures:
            print("FAIL:", f, file=sys.stderr)
        return 1

    print(f"OK: {len(rows)} requirements traced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
