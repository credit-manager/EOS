import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(user='eos', host='localhost', port=5432, database='eos_main', password='0100')
        result = await conn.fetchval('SELECT 1')
        print('Connection OK, result=' + str(result))
        await conn.close()
    except Exception as e:
        print('Connection FAILED - ' + type(e).__name__ + ': ' + str(e))

asyncio.run(test())