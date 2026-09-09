import sys
sys.path.insert(0, r"D:\EOS\Eos final")
from core.auth import create_test_token

token = create_test_token(
    tenant_id="demo-tenant",
    user_id="admin-001",
    email="admin@eos-demo.com",
    roles=["admin"]
)
print("TOKEN:", token)
print()
print("Login credentials:")
print("  Tenant ID:  demo-tenant")
print("  Email:      admin@eos-demo.com")
print("  Password:   any text (test mode)")
