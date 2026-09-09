import urllib.request

r = urllib.request.urlopen("http://127.0.0.1:8001/app", timeout=5)
html = r.read().decode()

# Print first 2000 chars
print(html[:2000])
print("...")
print("=== LAST 500 chars ===")
print(html[-500:])
