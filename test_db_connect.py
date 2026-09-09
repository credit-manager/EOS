import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect('postgresql+asyncpg://eos:0100@localhost:5432/eos_main')
        result = await conn.fetchval('SELECT 1')
        print(f"Connected! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())