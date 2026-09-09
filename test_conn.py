import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(host='localhost', port=5432, user='postgres', database='postgres')
        result = await conn.fetchval('SELECT 1')
        print(f"Connected as postgres! Result: {result}")
        await conn.close()
        
        # Now try to alter the eos user password
        conn2 = await asyncpg.connect(host='localhost', port=5432, user='postgres', database='eos_main')
        await conn2.execute("ALTER USER eos WITH PASSWORD 'Eos_2026_Secure'")
        print("Password altered successfully!")
        await conn2.close()
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())