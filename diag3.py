#!/usr/bin/env python3
import subprocess
import sys
import os

backend_dir = r"D:\EOS\Eos final\eos-system\backend"
log_stdout = os.path.join(os.getenv("TEMP", "."), "diag_stdout.log")
log_stderr = os.path.join(os.getenv("TEMP", "."), "diag_stderr.log")

# Remove old logs
if os.path.exists(log_stdout): os.remove(log_stdout)
if os.path.exists(log_stderr): os.remove(log_stderr)

# Start uvicorn
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd=backend_dir,
    stdout=open(log_stdout, "w"),
    stderr=open(log_stderr, "w")
)

# Wait 10 seconds
import time
time.sleep(10)

# Check process
if proc.poll() is None:
    print("Process still running after 10 seconds")
else:
    print("Process terminated with code:", proc.poll())
    
# Read logs
with open(log_stdout, "r") as f:
    print("=== STDOUT ===")
    print(f.read())
    
with open(log_stderr, "r") as f:
    print("=== STDERR ===")
    print(f.read())