import uvicorn
import sys
import os
import asyncio

sys.path.insert(0, r"D:\EOS\Eos final\eos-system\backend")
os.chdir(r"D:\EOS\Eos final\eos-system\backend")

# First, test the database connection
async def test_db():
    try:
        import asyncpg
        conn = await asyncpg.connect(user='eos', host='localhost', port=5432, database='eos_main', password='0100')
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print("Database connection: OK, result=" + str(result))
        return True
    except Exception as e:
        print("Database connection: FAILED - " + type(e).__name__)
        return False

# Test the FastAPI app import and basic setup
async def test_app():
    try:
        from app.main import create_application
        app = create_application()
        print("FastAPI application: OK")
        return True
    except Exception as e:
        print("FastAPI application: FAILED - " + type(e).__name__)
        return False

# Run tests
print("Running tests...")
db_ok = asyncio.run(test_db())
print()
app_ok = asyncio.run(test_app())

print("\n" + "="*50)
if db_ok and app_ok:
    print("All systems operational")
else:
    print("Some systems failed - Check errors above")