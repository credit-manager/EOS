from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SERVER = ROOT / "app_server.py"
DOCKERFILE = ROOT / "Dockerfile"
FRONTEND_PACKAGE = ROOT / "erp-system" / "frontend" / "package.json"


def test_production_server_intercepts_root_for_canonical_frontend():
    source = APP_SERVER.read_text(encoding="utf-8")
    assert '@app.middleware("http")' in source
    assert "serve_canonical_frontend" in source
    assert 'request.url.path == "/"' in source
    assert 'INDEX_FILE.is_file()' in source


def test_production_server_does_not_add_shadowing_root_route():
    source = APP_SERVER.read_text(encoding="utf-8")
    assert '@app.get("/")' not in source


def test_production_container_builds_and_copies_canonical_frontend():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    package = FRONTEND_PACKAGE.read_text(encoding="utf-8")
    assert "erp-system/frontend/package-lock.json" in dockerfile
    assert "npm ci --no-audit --no-fund" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "/app/erp-system/frontend/dist" in dockerfile
    assert '"build": "tsc && vite build"' in package
