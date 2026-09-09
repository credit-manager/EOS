import subprocess
import time

# Step 1: Kill any existing postgres processes
print("Step 1: Killing existing postgres processes...")
result = subprocess.run(
    ['taskkill', '/F', '/IM', 'postgres.exe'],
    capture_output=True, text=True
)
print(f"  Kill return code: {result.returncode}")
time.sleep(3)

# Step 2: Try to start PostgreSQL using pg_ctl
print("\nStep 2: Starting PostgreSQL with pg_ctl...")
pg_ctl_path = r'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe'
data_dir = r'C:\Program Files\PostgreSQL\18\data'
config_file = r'C:\Program Files\PostgreSQL\18\data\postgresql.conf'

cmd = [pg_ctl_path, 'start', '-W', data_dir]
# Actually the syntax is: pg_ctl start -D data_dir -w
cmd = [pg_ctl_path, 'start', '-D', data_dir, '-w']
print(f"  Running: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
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
    conn = psycopg2.connect(
        host='localhost', 
        dbname='eos_main', 
        user='postgres',
        password=''
    )
    cur = conn.cursor()
    cur.execute('SELECT 1')
    print(f"✅ Connection SUCCESS: {cur.fetchone()}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection FAILED: {type(e).__name__}: {str(e)[:200]}")
"