import asyncio
import asyncpg

async def test():
    # Test 1: Direct connection with exact parameters
    try:
        conn = await asyncpg.connect('postgresql+asyncpg://eos:0100@localhost:5432/eos_main')
        result = await conn.fetchval('SELECT 1')
        print('Test 1 PASS: Direct URL connection OK, result=' + str(result))
        await conn.close()
    except Exception as e:
        print('Test 1 FAIL: ' + type(e).__name__ + ': ' + str(e)[:200])
    
    # Test 2: Connection with explicit parameters
    try:
        conn = await asyncpg.connect(user='eos', password='0100', host='localhost', port=5432, database='eos_main')
        result = await conn.fetchval('SELECT 1')
        print('Test 2 PASS: Explicit params connection OK, result=' + str(result))
        await conn.close()
    except Exception as e:
        print('Test 2 FAIL: ' + type(e).__name__ + ': ' + str(e)[:200])
    
    # Test 3: Check if engine creation works
    from sqlalchemy import create_engine
    try:
        engine = create_engine('postgresql+asyncpg://eos:0100@localhost:5432/eos_main')
        print('Test 3 PASS: SQLAlchemy engine creation OK')
    except Exception as e:
        print('Test 3 FAIL: ' + type(e).__name__ + ': ' + str(e)[:200])

asyncio.run(test())