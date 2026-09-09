import urllib.request, json

data = json.dumps({
    "email": "admin@demo.com",
    "password": "admin123"
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8001/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    r = urllib.request.urlopen(req, timeout=10)
    result = json.loads(r.read())
    print("LOGIN SUCCESS!")
    user = result.get("data", {}).get("user", {})
    print(f"  Name:  {user.get('first_name')} {user.get('last_name')}")
    print(f"  Email: {user.get('email')}")
    print(f"  Tenant: {user.get('tenant_id')}")
    print(f"  Role:  {user.get('role')}")
    print(f"\nToken: {result['data']['access_token'][:50]}...")
except Exception as e:
    print(f"LOGIN FAILED: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode())
