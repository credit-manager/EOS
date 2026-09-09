import subprocess
import sys

pg_ctl_path = r"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
data_dir = r"C:\Program Files\PostgreSQL\18\data"

# Build command carefully - use list form to avoid shell parsing issues
cmd = [pg_ctl_path, "start", "-D", data_dir]
print(f"Attempting to start PostgreSQL...")
print(f"Command: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(f"Exit code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr[:500]}")
except subprocess.TimeoutExpired as e:
    print(f"Timeout after 30 seconds")
    print(f"STDOUT: {e.stdout}")
    print(f"STDERR: {e.stderr[:500] if e.stderr else 'none'}")