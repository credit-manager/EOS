import subprocess
import sys

# Try using pg_ctl to restart PostgreSQL
pg_ctl_path = r"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
data_dir = r"C:\Program Files\PostgreSQL\18\data"

cmd = [pg_ctl_path, "restart", "-D", data_dir, "-m", "fast"]
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
except subprocess.TimeoutExpired as e:
    print("Timeout:", e)
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr)