import httpx, json

r = httpx.post("http://localhost:8001/api/v1/auth/register", json={
    "company_name": "Test Company",
    "company_name_ar": "Test",
    "email": "manual3@test.com",
    "password": "Pass123!",
    "industry": "technology",
})
print(f"Status: {r.status_code}")
print(f"Body: {r.text[:500]}")
