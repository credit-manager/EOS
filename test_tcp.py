import asyncio
import asyncpg

async def test_tcp():
    # Try TCP connection without specifying host (defaults to localhost)
    configs = [
        {"user": "eos", "password": "0100", "database": "eos_main"},
        {"user": "postgres", "password": "", "database": "postgres"},
        {"user": "eos", "password": "", "database": "eos_main"},
        {"user": "", "password": "", "database": "postgres"},
    ]
    
    for i, cfg in enumerate(configs, 1):
        try:
            conn = await asyncpg.connect(**cfg)
            result = await conn.fetchval('SELECT 1')
            print(f"Config {i} ({cfg}): Connected! Result: {result}")
            await conn.close()
        except Exception as e:
            print(f"Config {i} ({cfg}): {type(e).__name__}: {str(e)[:80]}")

asyncio.run(test_tcp())