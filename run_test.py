import asyncio
import httpx
import uuid

BASE = "http://localhost:8001/api/v1"

async def test():
    async with httpx.AsyncClient() as c:
        try:
            r = await c.get(f"{BASE}/health")
            print(f"Health endpoint: status={r.status_code}")
        except Exception as e:
            print(f"Health endpoint: ERROR - {type(e).__name__}")
        
        # Try register
        try:
            r = await c.post(f"{BASE}/auth/register", json={
                "email": "test@example.com",
                "password": "testpass123",
                "full_name": "Test User"
            })
            print(f"Register: status={r.status_code}")
        except Exception as e:
            print(f"Register: ERROR - {type(e).__name__}")

asyncio.run(test())