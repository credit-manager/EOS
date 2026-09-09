import urllib.request, json

# 1. Check if the React index.html loads
r = urllib.request.urlopen("http://127.0.0.1:8001/ui", timeout=5)
html = r.read().decode()
print("=== /ui HTML ===")
print(f"Size: {len(html)} bytes")
print(html[:500])
print("...")

# 2. Check the JS bundle
import re
scripts = re.findall(r'src="([^"]+)"', html)
print(f"\nScripts found: {scripts}")

for s in scripts:
    url = f"http://127.0.0.1:8001{s}"
    try:
        r2 = urllib.request.urlopen(url, timeout=5)
        data = r2.read()
        print(f"  {s}: {r2.status} ({len(data)} bytes)")
    except Exception as e:
        print(f"  {s}: ERROR {e}")

# 3. Check CSS
links = re.findall(r'href="([^"]+\.css)"', html)
print(f"\nCSS found: {links}")
for l in links:
    url = f"http://127.0.0.1:8001{l}"
    try:
        r2 = urllib.request.urlopen(url, timeout=5)
        print(f"  {l}: {r2.status} ({len(r2.read())} bytes)")
    except Exception as e:
        print(f"  {l}: ERROR {e}")
