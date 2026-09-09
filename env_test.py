import asyncio
import asyncpg
import os

# Test 1: Without environment variables
async def test1():
    try:
        conn = await asyncpg.connect(user='eos', host='localhost', port=5432, database='eos_main', password='0100')
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print('Test 1 PASS: Direct connect with explicit pwd')
    except Exception as e:
        print('Test 1 FAIL: ' + type(e).__name__)

# Test 2: With PGHOST env var
async def test2():
    os.environ['PGHOST'] = 'localhost'
    try:
        conn = await asyncpg.connect(host='localhost', port=5432, user='eos', password='0100', database='eos_main')
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print('Test 2 PASS: With PGHOST=localhost env')
    except Exception as e:
        print('Test 2 FAIL: ' + type(e).__name__)
    finally:
        del os.environ['PGHOST']

# Test 3 With PGUSER env var
async def test3():
    os.environ['PGUSER'] = 'eos'
    try:
        conn = await asyncpg.connect(host='localhost', port=5432, user='eos', password='0100', database='eos_main')
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print('Test 3 PASS: With PGUSER=eos env')
    except Exception as e:
        print('Test 3 FAIL: ' + type(e).__name__)
    finally:
        del os.environ['PGUSER']

# Test 4: Without any env vars
async def test4():
    try:
        # Make sure env vars are clean
        env_keys = ['PGHOST', 'PGUSER', 'PGPASSWORD']
        for k in env_keys:
            os.environ.pop(k, None)
        conn = await asyncpg.connect(user='eos', password='0100', host='localhost', port=5432, database='eos_main')
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print('Test 4 PASS: Without env vars, explicit params')
    except Exception as e:
        print('Test 4 FAIL: ' + type(e).__name__)

asyncio.run(test1())
print()
asyncio.run(test2())
print()
asyncio.run(test3())
print()
asyncio.run(test4())