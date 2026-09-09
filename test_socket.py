import asyncio
import asyncpg

async def test_local_socket():
    # Try with empty PGHOST - local socket
    try:
        conn = await asyncpg.connect(user='postgres', database='postgres')
        result = await conn.fetchval('SELECT 1')
        print(f"Local socket connected! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"Local socket Error: {type(e).__name__}: {e}")

asyncio.run(test_local_socket())