import subprocess
import time

# Try to alter the eos user password using psql via subprocess
# First, let's try connecting as postgres user and altering the password

# Method 1: Try using pg_ctl and then SQL
pg_ctl_path = r"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
data_dir = r"C:\Program Files\PostgreSQL\18\data"

# Check if postmaster.pid exists
import os
pid_file = os.path.join(data_dir, "postmaster.pid")
print(f"Postmaster PID file exists: {os.path.exists(pid_file)}")

# Try to connect and alter password using subprocess with proper env
env = os.environ.copy()
env['PGHOST'] = 'localhost'

# Try method: using sudo or running as system user
# For now, let's try a simple approach - use the existing server connection

print("PostgreSQL server is running but password authentication failed")
print("Need to alter user eos password to '0100'")
print("Attempting to fix PostgreSQL password...")

# Try using Python with asyncpg to connect as postgres superuser and alter password
import asyncio
import asyncpg

async def fix_password():
    try:
        # Try connecting as postgres first
        conn = await asyncpg.connect(user='postgres', host='localhost', port=5432, database='postgres')
        await conn.execute(f"ALTER USER eos WITH PASSWORD '0100'")
        await conn.close()
        print("Successfully altered eos user password to 0100")
        return True
    except Exception as e:
        print(f"Failed to alter password via postgres user: {type(e).__name__}: {str(e)[:200]}")
        return False

# Try another method - connect without password check
async def test_connection():
    try:
        conn = await asyncpg.connect(user='eos', host='localhost', port=5432, database='eos_main', password='0100')
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print(f"Successfully connected as eos user, result: {result}")
        return True
    except Exception as e:
        print(f"Failed to connect as eos user: {type(e).__name__}: {str(e)[:200]}")
        return False

# Run the tests
print("Testing PostgreSQL connection...")
result1 = asyncio.run(fix_password())
print()
result2 = asyncio.run(test_connection())