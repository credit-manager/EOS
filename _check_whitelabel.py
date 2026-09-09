import urllib.request, json

try:
    r = urllib.request.urlopen("http://127.0.0.1:8001/api/v1/whitelabel/public/127.0.0.1", timeout=5)
    data = json.loads(r.read())
    print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
