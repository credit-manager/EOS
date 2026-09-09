"""Static anti-regression checks for commercial production readiness."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_DDL_MARKERS = (
    "CREATE TABLE IF NOT EXISTS",
    "Base.metadata.create_all",
)
STUB_MARKERS = (
    '"cost_of_goods": 0',
    '"cogs": 0',
    '"operating": 0',
    'return {"error": f"Report for {industry} not implemented"}',
)


def fail_if_present(path: Path, markers: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [marker for marker in markers if marker in text]


def main() -> int:
    violations: list[str] = []

    for path in ROOT.joinpath("core").rglob("*.py"):
        if path.name in {"payment_engine.py"}:
            markers = fail_if_present(path, RUNTIME_DDL_MARKERS)
            violations.extend(f"{path.relative_to(ROOT)}: runtime DDL marker {marker!r}" for marker in markers)

    reporting = ROOT / "core" / "reporting_engine.py"
    if reporting.exists():
        markers = fail_if_present(reporting, STUB_MARKERS)
        violations.extend(f"{reporting.relative_to(ROOT)}: financial/reporting stub {marker!r}" for marker in markers)

    if violations:
        print("Commercial static gate FAILED")
        print("\n".join(violations))
        return 1
    print("Commercial static gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
