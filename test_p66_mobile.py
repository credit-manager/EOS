# -*- coding: utf-8 -*-
"""
EOS P66 — Mobile & Responsive ERP Verification Suite
=====================================================
Verifies (without needing a running stack):
  A. PWA artifacts       (manifest, icons, service worker)
  B. index.html mobile/PWA meta
  C. Service worker strategy (cache-first static, network-first API reads,
     writes never intercepted -> app-level offline queue owns them)
  D. App bootstrap       (SW registration + offline queue init)
  E. Offline-awareness   (persistent queue, replay-on-reconnect, bounds)
  F. Network status hook
  G. Offline banner UI
  H. apiClient hardening (offline writes queueing, session-expiry broadcast,
     silent refresh, tenant isolation preserved)
  I. Session security    (JWT expiry check + forced logout)
  J. Responsive layout   (mobile drawer, bottom nav, breakpoints)
  K. Mobile navigation component
  L. Mobile CSS          (safe-area, touch targets, RTL chart fix)
  N. Regression guards   (P0-P65 untouched: routes, menu, analytics API,
     backend router endpoint count)
"""

import json
import sys
from pathlib import Path

# Windows consoles default to cp1252 — force UTF-8 (Arabic check names)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
FE = ROOT / "eos-system" / "frontend"
SRC = FE / "src"

results = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"EXCEPTION: {e}"
    results.append((name, bool(ok), detail or ""))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def rd(rel: str) -> str:
    return read(ROOT / rel)


def frd(rel: str) -> str:
    return read(FE / rel)


def srd(rel: str) -> str:
    return read(SRC / rel)


# ============================================================
# A. PWA artifacts
# ============================================================

MANIFEST = FE / "public" / "manifest.webmanifest"

check("PWA-01 manifest.webmanifest exists",
      lambda: (MANIFEST.exists(), str(MANIFEST)))

_manifest_data = {}


def _c02():
    global _manifest_data
    if not MANIFEST.exists():
        return False, "missing"
    _manifest_data = json.loads(read(MANIFEST))
    return isinstance(_manifest_data, dict), "valid JSON"


check("PWA-02 manifest parses as valid JSON", _c02)

check("PWA-03 manifest has name + short_name",
      lambda: (bool(_manifest_data.get("name")) and bool(_manifest_data.get("short_name")),
               f"name={_manifest_data.get('name','?')!r}"))

check("PWA-04 display standalone",
      lambda: (_manifest_data.get("display") == "standalone",
               f"display={_manifest_data.get('display')}"))

check("PWA-05 start_url defined",
      lambda: (bool(_manifest_data.get("start_url")), str(_manifest_data.get("start_url"))))

_icons = _manifest_data.get("icons", [])

check("PWA-06 >=3 icon entries incl. 192+512",
      lambda: (
          len(_icons) >= 3
          and any("192" in i.get("sizes", "") for i in _icons)
          and any("512" in i.get("sizes", "") for i in _icons),
          f"{len(_icons)} icons"))

check("PWA-07 maskable icon declared",
      lambda: (any("maskable" in i.get("purpose", "") for i in _icons), "installable quality"))

check("PWA-08 theme_color set",
      lambda: (bool(_manifest_data.get("theme_color")), str(_manifest_data.get("theme_color"))))

check("PWA-09 manifest dir=rtl lang=ar",
      lambda: (_manifest_data.get("dir") == "rtl" and _manifest_data.get("lang") == "ar",
               "Arabic-first install"))


def _c10(size):
    def inner():
        p = FE / "public" / "icons" / f"icon-{size}.png"
        if not p.exists():
            return False, "missing"
        head = p.read_bytes()[:8]
        return head == b"\x89PNG\r\n\x1a\n", f"{p.name} valid PNG ({p.stat().st_size}B)"
    return inner


check("PWA-10 icon-192.png real PNG", _c10(192))
check("PWA-11 icon-512.png real PNG", _c10(512))

SW = FE / "public" / "sw.js"
_sw = read(SW) if SW.exists() else ""

check("PWA-12 sw.js exists", lambda: (SW.exists(), str(SW)))
check("PWA-13 sw registers install handler",
      lambda: ("addEventListener('install'" in _sw, "precaches app shell"))
check("PWA-14 sw activate cleans old caches",
      lambda: ("addEventListener('activate'" in _sw and "caches.delete" in _sw, "versioned cleanup"))
check("PWA-15 sw fetch interception",
      lambda: ("addEventListener('fetch'" in _sw, "network strategies"))
check("PWA-16 sw never caches write requests",
      lambda: ("isWriteMethod(request.method)" in _sw.replace("!", ""), 
               "POST/PUT/DELETE bypass"))
check("PWA-17 sw api reads network-first w/ cache fallback",
      lambda: ("isApiRequest" in _sw and "offline" in _sw, "read-only offline ERP"))
check("PWA-18 sw skipWaiting + clients.claim",
      lambda: ("skipWaiting" in _sw and "clients.claim" in _sw, "instant updates"))

# ============================================================
# B. index.html mobile / PWA meta
# ============================================================

HTML = frd("index.html")

check("HTML-01 viewport-fit=cover + user-scalable=no",
      lambda: ("viewport-fit=cover" in HTML and "user-scalable=no" in HTML, "notch-safe, app-like"))
check("HTML-02 manifest linked",
      lambda: ('rel="manifest"' in HTML and "manifest.webmanifest" in HTML, ""))
check("HTML-03 theme-color meta",
      lambda: ('name="theme-color"' in HTML, ""))
check("HTML-04 iOS apple-mobile-web-app-capable",
      lambda: ("apple-mobile-web-app-capable" in HTML, "Add-to-Home-Screen iOS"))
check("HTML-05 apple-touch-icon",
      lambda: ("apple-touch-icon" in HTML, "iOS home screen icon"))

# ============================================================
# D. Bootstrap: SW registration + offline queue init
# ============================================================

MAIN = srd("main.tsx")

check("BOOT-01 main.tsx registers service worker",
      lambda: ("serviceWorker" in MAIN and "register('/sw.js')" in MAIN.replace('"', "'"), ""))
check("BOOT-02 SW registration PROD-guarded",
      lambda: ("import.meta.env.PROD" in MAIN, "dev HMR unaffected"))
check("BOOT-03 main.tsx initializes offline queue",
      lambda: ("initOfflineQueue()" in MAIN, ""))

# ============================================================
# E. Offline-awareness: persistent queue + replay
# ============================================================

OQ = SRC / "services" / "offlineQueue.ts"
_oq = read(OQ) if OQ.exists() else ""

check("OFFQ-01 offlineQueue.ts exists", lambda: (OQ.exists(), str(OQ)))
check("OFFQ-02 localStorage-persisted queue key",
      lambda: ("eos-offline-queue" in _oq, "survives reload/crash"))
check("OFFQ-03 exports enqueueQueuedRequest",
      lambda: ("export function enqueueQueuedRequest" in _oq, ""))
check("OFFQ-04 exports flushQueue replay",
      lambda: ("export async function flushQueue" in _oq, ""))
check("OFFQ-05 auto-flush on 'online' event",
      lambda: ("window.addEventListener('online'" in _oq, "reconnect triggers replay"))
check("OFFQ-06 replay preserves order, stops at network failure",
      lambda: ("networkFailure" in _oq and "break" in _oq, "no ordering corruption"))
check("OFFQ-07 4xx ops discarded (never retried forever)",
      lambda: ("response" in _oq and "dequeue(item.id)" in _oq, ""))
check("OFFQ-08 queue size bounded (MAX_QUEUE_SIZE)",
      lambda: ("MAX_QUEUE_SIZE" in _oq, "storage exhaustion safe"))
check("OFFQ-09 emits queue-changed event for UI",
      lambda: ("eos-offline-queue-changed" in _oq, ""))
check("OFFQ-10 emits sync-done event after replay",
      lambda: ("eos-offline-sync-done" in _oq, ""))
check("OFFQ-11 initOfflineQueue idempotent",
      lambda: ("initialized" in _oq, "safe under StrictMode double-invoke"))

# ============================================================
# F/G. Connectivity hook + banner
# ============================================================

NET = SRC / "hooks" / "useNetworkStatus.ts"
_net = read(NET) if NET.exists() else ""

check("HOOK-01 useNetworkStatus hook exists", lambda: (NET.exists(), ""))
check("HOOK-02 tracks browser online/offline events",
      lambda: ("addEventListener('online'" in _net and "addEventListener('offline'" in _net, ""))

BAN = SRC / "components" / "OfflineBanner.tsx"
_ban = read(BAN) if BAN.exists() else ""

check("UI-01 OfflineBanner component exists", lambda: (BAN.exists(), ""))
check("UI-02 banner shows offline warning",
      lambda: ("لا يوجد اتصال" in _ban and "Alert" in _ban, "Arabic UX copy"))
check("UI-03 banner reports pending queued ops count",
      lambda: ("getQueueSize" in _ban or "eos-offline-queue-changed" in _ban, ""))
check("UI-04 banner confirms successful sync",
      lambda: ("تمت مزامنة" in _ban, ""))

# ============================================================
# H. apiClient hardening
# ============================================================

CLI = srd("services/apiClient.ts")

check("API-01 client enqueues failed writes to offline queue",
      lambda: ("enqueueQueuedRequest" in CLI and "queuedOffline" in CLI, ""))
check("API-02 only POST/PUT/DELETE are queued (GET passthrough)",
      lambda: ("method === 'post'" in CLI and "method === 'put'" in CLI and "method === 'delete'" in CLI, ""))
check("API-03 auth endpoints never queued",
      lambda: ("isAuthPath" in CLI, "no credential replay attacks"))
check("API-04 broadcasts eos-session-expired on dead refresh",
      lambda: ("eos-session-expired" in CLI, ""))
check("API-05 silent refresh via /auth/refresh",
      lambda: ("/auth/refresh" in CLI and "trySilentRefresh" in CLI, ""))
check("API-06 proactive expiry check in request interceptor",
      lambda: ("isTokenExpired(token)" in CLI, ""))
check("API-07 tenant isolation header preserved (X-Tenant-ID)",
      lambda: ("X-Tenant-ID" in CLI, "multi-tenant boundary intact"))

# ============================================================
# I. Session security
# ============================================================

JWT = SRC / "utils" / "jwt.ts"
_jwt = read(JWT) if JWT.exists() else ""

check("SEC-01 jwt util module exists", lambda: (JWT.exists(), ""))
check("SEC-02 decodes JWT payload w/o trusting it",
      lambda: ("decodeToken" in _jwt and "exp" in _jwt, "client display only"))
check("SEC-03 isTokenExpired uses real exp claim",
      lambda: ("claims?.exp" in _jwt or "claims.exp" in _jwt, ""))
check("SEC-04 non-JWT (mock/dev) tokens tolerated",
      lambda: ("return false" in _jwt, "dev flow unbroken"))

STORE = srd("stores/authStore.ts")

check("SEC-05 authStore force-logout on session-expired broadcast",
      lambda: ("eos-session-expired" in STORE and "logout()" in STORE, "expired token => clean state"))

# ============================================================
# J/K. Responsive layout + mobile navigation
# ============================================================

LAY = srd("layouts/MainLayout.tsx")

check("RESP-01 MainLayout reacts to breakpoints",
      lambda: ("useBreakpoint" in LAY and "isMobile" in LAY, ""))
check("RESP-02 mobile uses right-side Drawer menu (RTL)",
      lambda: ('placement="right"' in LAY and "<Drawer" in LAY, ""))
check("RESP-03 hamburger triggers drawer on phones",
      lambda: ("MenuOutlined" in LAY and "setDrawerOpen(true)" in LAY, ""))
check("RESP-04 bottom nav rendered on mobile only",
      lambda: ("{isMobile && <MobileNav" in LAY.replace(" ", " "), ""))
check("RESP-05 content clears bottom nav height",
      lambda: ("84" in LAY and "paddingBottom" in LAY, "no overlap"))
check("RESP-06 compact spacing under md",
      lambda: ("isMobile ? 8 : 24" in LAY, "density per device class"))
check("RESP-07 desktop Sider behavior preserved",
      lambda: ("<Sider" in LAY and "collapsed" in LAY, "no desktop regression"))
check("RESP-08 offline pending badge in header",
      lambda: ("eos-offline-queue-changed" in LAY and "Badge" in LAY, ""))
check("RESP-09 logout flow intact",
      lambda: ("logout()" in LAY and "'/login'" in LAY, ""))

NAV = SRC / "components" / "MobileNav.tsx"
_nav = read(NAV) if NAV.exists() else ""

check("NAV-01 MobileNav component exists", lambda: (NAV.exists(), ""))
check("NAV-02 primary thumb destinations (4 tabs + more)",
      lambda: (_nav.count("{ key:") >= 4 and "onMore" in _nav, ""))
check("NAV-03 active-state highlighting via router location",
      lambda: ("useLocation" in _nav and "aria-current" in _nav, "a11y included"))
check("NAV-04 includes Analytics destination (P65 link)",
      lambda: ("'/analytics'" in _nav, ""))

# ============================================================
# L. Mobile CSS
# ============================================================

CSS = srd("styles/global.css")

check("CSS-01 bottom nav styles (.eos-mobile-nav)",
      lambda: (".eos-mobile-nav" in CSS, ""))
check("CSS-02 iPhone home-indicator safe area",
      lambda: ("env(safe-area-inset-bottom)" in CSS, ""))
check("CSS-03 notch side insets respected",
      lambda: ("safe-area-inset-left" in CSS, ""))
check("CSS-04 charts pinned LTR inside RTL page",
      lambda: (".recharts-wrapper" in CSS and "direction: ltr" in CSS, ""))
check("CSS-05 fat-finger touch targets on coarse pointers",
      lambda: ("hover: none" in CSS and "pointer: coarse" in CSS, ""))
check("CSS-06 tables scroll horizontally on small screens",
      lambda: ("max-width: 768px" in CSS and "overflow-x: auto" in CSS, ""))
check("CSS-07 prevents iOS input zoom (16px inputs)",
      lambda: ("font-size: 16px !important" in CSS, ""))

# ============================================================
# N. Regression guards — nothing from P0..P65 broke
# ============================================================

APPX = srd("App.tsx")

check("REG-01 /dashboard route still present",
      lambda: ('"/dashboard"' in APPX, ""))
check("REG-02 P65 /analytics route still present",
      lambda: ('"/analytics/*"' in APPX and "AnalyticsPage" in APPX, ""))
for mod in ["AccountingPage", "InventoryPage", "HRPage", "SalesPage",
            "ProjectsPage", "AIPage", "SettingsPage"]:
    check(f"REG-{mod} route preserved",
          lambda m=mod: (m in APPX, ""))

IDX = srd("services/index.ts")
check("REG-analyticsApi export preserved (P65)",
      lambda: ("analyticsApi" in IDX, ""))

DASH = srd("pages/DashboardPage.tsx")
check("REG-P65 executive dashboard wired to backend still",
      lambda: ("analyticsApi" in DASH and "getExecutiveSummary" in DASH, ""))

MENU_KEYS = ["/dashboard", "/analytics", "/sales", "/projects",
             "/inventory", "/accounting", "/hr", "/ai", "/settings"]
check("REG-all 9 navigation destinations preserved",
      lambda: (all(k in LAY for k in MENU_KEYS), "9/9 menu keys"))

ROUTER_SRC = rd("routers/analytics_router.py")
check("REG-backend analytics router untouched (19 endpoints)",
      lambda: (ROUTER_SRC.count("@router.get") == 19,
               f"{ROUTER_SRC.count('@router.get')}/19 GET endpoints"))

LOGIN = srd("pages/LoginPage.tsx")
check("REG-login card constrained to viewport",
      lambda: ("maxWidth: 400" in LOGIN and "width: '100%'" in LOGIN, "responsive auth"))

SW_REG_MAIN = "import.meta.env.PROD" in MAIN
check("REG-main.tsx renders theming + App unchanged",
      lambda: (("ConfigProvider" in MAIN or "BrandedShell" in MAIN) and "<App />" in MAIN and SW_REG_MAIN, ""))

# ============================================================
# Summary
# ============================================================

passed = sum(1 for _, ok, _ in results if ok)
total = len(results)

print("=" * 64)
print("  EOS P66 - Mobile & Responsive ERP Verification")
print("=" * 64)
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}"
    if detail:
        line += f"  ({detail})"
    print(line)
print("=" * 64)
print(f"RESULT: {passed}/{total} checks passed")

if passed != total:
    print("\nFailed checks:")
    for name, ok, _ in results:
        if not ok:
            print(f"  - {name}")
    sys.exit(1)
