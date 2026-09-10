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

    payment_engine = ROOT / "core" / "payment_engine.py"
    if payment_engine.exists():
        markers = fail_if_present(payment_engine, RUNTIME_DDL_MARKERS)
        violations.extend(f"{payment_engine.relative_to(ROOT)}: runtime DDL marker {marker!r}" for marker in markers)

    builder_engine = ROOT / "core" / "builder_engine.py"
    if builder_engine.exists():
        markers = fail_if_present(builder_engine, ("CREATE TABLE IF NOT EXISTS", "ALTER TABLE public."))
        violations.extend(f"{builder_engine.relative_to(ROOT)}: privileged builder DDL marker {marker!r}" for marker in markers)

    reporting = ROOT / "core" / "reporting_engine.py"
    if reporting.exists():
        markers = fail_if_present(reporting, STUB_MARKERS)
        violations.extend(f"{reporting.relative_to(ROOT)}: financial/reporting stub {marker!r}" for marker in markers)

    frontend_wrapper = ROOT / "app_server.py"
    entrypoint = ROOT / "docker" / "entrypoint.sh"
    dockerfile = ROOT / "Dockerfile"
    if not frontend_wrapper.is_file():
        violations.append("app_server.py: canonical frontend ASGI wrapper is missing")
    else:
        wrapper = frontend_wrapper.read_text(encoding="utf-8")
        for marker in ("from main import app", "erp-system", "frontend", "index.html", "FileResponse"):
            if marker not in wrapper:
                violations.append(f"app_server.py: missing frontend runtime marker {marker!r}")
    if not entrypoint.is_file():
        violations.append("docker/entrypoint.sh: runtime entrypoint is missing")
    else:
        entrypoint_text = entrypoint.read_text(encoding="utf-8")
        if "gunicorn app_server:app" not in entrypoint_text:
            violations.append("docker/entrypoint.sh: must launch app_server:app")
    if not dockerfile.is_file():
        violations.append("Dockerfile: production image definition is missing")
    else:
        dockerfile_text = dockerfile.read_text(encoding="utf-8")
        if "COPY --from=frontend-builder" not in dockerfile_text or "/erp-system/frontend/dist" not in dockerfile_text:
            violations.append("Dockerfile: canonical frontend build artifact is not copied into runtime image")

    if violations:
        print("Commercial static gate FAILED")
        print("\n".join(violations))
        return 1
    print("Commercial static gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
