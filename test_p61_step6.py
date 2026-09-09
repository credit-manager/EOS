"""P61 Step 6 — Landing / Signup / Login UI E2E"""
import httpx, sys, subprocess, time, os

BASE = "http://127.0.0.1:8000"
p, f = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, f
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def log(msg):
    results.append(f"  ---  {msg}")


def start_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(6)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    print("=" * 60)
    print("  P61 STEP 6 — Landing / Signup / Login UI E2E")
    print("=" * 60)

    proc = start_server()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        # ── Step 1: Root endpoint ──
        log("STEP 1: Root endpoint")
        r = c.get("/")
        t("Root returns 200", r.status_code, 200)
        t("Root has message", "message" in r.json(), True)

        # ── Step 2: Landing page ──
        log("STEP 2: Landing page (/app)")
        r = c.get("/app")
        t("Landing page returns 200", r.status_code, 200)
        t("Landing page is HTML", "text/html" in r.headers.get("content-type", ""), True)
        body = r.text
        t("Has EOS title", "EOS" in body, True)
        t("Has signup form", "signup" in body.lower(), True)
        t("Has login form", "login" in body.lower(), True)

        # ── Step 3: API docs accessible ──
        log("STEP 3: API docs accessible")
        r = c.get("/docs")
        t("Swagger UI returns 200", r.status_code, 200)

        # ── Step 4: OpenAPI JSON ──
        log("STEP 4: OpenAPI JSON")
        r = c.get("/openapi.json")
        t("OpenAPI JSON returns 200", r.status_code, 200)
        t("Has paths", "paths" in r.json(), True)

        # ── Step 5: Auth endpoints listed ──
        log("STEP 5: Auth endpoints in OpenAPI")
        paths = r.json()["paths"]
        auth_paths = [p for p in paths if "/auth/" in p]
        t("Has auth endpoints", len(auth_paths) >= 5, True)

    finally:
        c.close()
        stop_server(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 60)
    print(f"  P61 STEP 6 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
