import subprocess
import time

# Kill any existing pg_ctl or postgres processes first by removing pid file
pid_file = r"C:\Program Files\PostgreSQL\18\data\postmaster.pid"
try:
    os.remove(pid_file)
    print(f"Removed {pid_file}")
except:
    print(f"{pid_file} not found (ok)")

# Try pg_ctl start with -N (dry run first to check) or just start
pg_ctl_path = r"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
data_dir = r"C:\Program Files\PostgreSQL\18\data"

# Try starting with minimal options
cmd = [pg_ctl_path, "start", "-D", data_dir, "-o", "-c config_file='" + r"C:\Program Files\PostgreSQL\18\data\postgresql.conf" + "'"]
print(f"Running: {' '.join(cmd)}")
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr[:1000] if result.stderr else "none")
    print("Return code:", result.returncode)
except subprocess.TimeoutExpired as e:
    print("Timeout - server might be starting in background")
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr[:1000] if e.stderr else "none")