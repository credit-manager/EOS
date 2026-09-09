import asyncio
import asyncpg

async def test():
    # Try connecting without password first
    try:
        conn = await asyncpg.connect(host='localhost', port=5432, user='postgres', database='postgres')
        result = await conn.fetchval('SELECT 1')
        print(f"Connected as postgres! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"Error connecting as postgres: {type(e).__name__}: {e}")
    
    # Try connecting as eos user
    try:
        conn = await asyncpg.connect(host='localhost', port=5432, user='eos', password='0100', database='eos_main')
        result = await conn.fetchval('SELECT 1')
        print(f"Connected as eos! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"Error connecting as eos: {type(e).__name__}: {e}")

asyncio.run(test())