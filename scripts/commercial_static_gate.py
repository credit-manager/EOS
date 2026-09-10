"""Static anti-regression checks for commercial production readiness."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_DDL_MARKERS = (
    "CREATE TABLE IF NOT EXISTS",
    "CREATE TABLE ",
    "ALTER TABLE ",
    "DROP TABLE ",
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

    # Runtime application code must never own database schema mutation.
    # DDL belongs in Alembic migrations or explicitly privileged builder SQL.
    for root_name in ("core", "routers"):
        root = ROOT / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            markers = fail_if_present(path, RUNTIME_DDL_MARKERS)
            violations.extend(
                f"{path.relative_to(ROOT)}: runtime DDL marker {marker!r}"
                for marker in markers
            )

    # Builder code has its own strict contract and may only reference the
    # dedicated privileged database function; direct table DDL is forbidden.
    builder_engine = ROOT / "core" / "builder_engine.py"
    if builder_engine.exists():
        markers = fail_if_present(builder_engine, ("CREATE TABLE IF NOT EXISTS", "ALTER TABLE public."))
        violations.extend(f"{builder_engine.relative_to(ROOT)}: privileged builder DDL marker {marker!r}" for marker in markers)

    reporting = ROOT / "core" / "reporting_engine.py"
    if reporting.exists():
        markers = fail_if_present(reporting, STUB_MARKERS)
        violations.extend(f"{reporting.relative_to(ROOT)}: financial/reporting stub {marker!r}" for marker in markers)

    control_plane = ROOT / "routers" / "control_plane.py"
    if control_plane.exists():
        # Passwords may be accepted once for provisioning, never returned in an API response.
        text = control_plane.read_text(encoding="utf-8")
        if '"admin_password": admin_password' in text or "'admin_password': admin_password" in text:
            violations.append("routers/control_plane.py: plaintext admin password must never be returned")

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
