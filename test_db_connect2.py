import asyncio
import asyncpg

async def test():
    try:
        # Try without asyncpg scheme prefix
        conn = await asyncpg.connect(host='localhost', port=5432, user='eos', password='0100', database='eos_main')
        result = await conn.fetchval('SELECT 1')
        print(f"Connected! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())