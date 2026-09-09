import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        "postgresql://eos:EOS_DB_2026_Local!@127.0.0.1:5432/eos_main"
    )
    print("SUCCESS: asyncpg -> eos_main")
    await conn.close()

asyncio.run(main())
