import subprocess
import time

pg_ctl_path = r"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
data_dir = r"C:\Program Files\PostgreSQL\18\data"

# Try to start PostgreSQL
cmd = [pg_ctl_path, "start", "-D", data_dir]
print(f"Running: {cmd}")
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr[:1000] if result.stderr else "none")
    print("Return code:", result.returncode)
except subprocess.TimeoutExpired as e:
    print("Timeout - server might be starting in background")
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr[:1000] if e.stderr else "none")