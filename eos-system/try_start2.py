import subprocess
import time

# Step 1: Kill existing postgres processes
print("Step 1: Killing existing postgres processes...")
result = subprocess.run(
    ['taskkill', '/F', '/IM', 'postgres.exe'],
    capture_output=True, text=True
)
print(f"  Kill result: {result.returncode}")
time.sleep(3)

# Step 2: Try to start PostgreSQL
print("\nStep 2: Starting PostgreSQL...")
try:
    result = subprocess.run(
        ['pg_ctl', 'start', '-D', r'C:\Program Files\PostgreSQL\18\data', '-w'],
        capture_output=True, text=True, timeout=15
    )
    print(f"  stdout: {result.stdout}")
    print(f"  stderr: {result.stderr[:200] if result.stderr else 'empty'}")
    print(f"  returncode: {result.returncode}")
except Exception as e:
    print(f"  Error: {e}")

time.sleep(3)

# Step 3: Try connecting
print("\nStep 3: Testing connection...")
import psycopg2
try:
    conn = psycopg2.connect(host='localhost', dbname='eos_main', user='postgres', password='')
    cur = conn.cursor()
    cur.execute('SELECT 1')
    print(f"✅ Connection SUCCESS: {cur.fetchone()}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection FAILED: {type(e).__name__}")
"