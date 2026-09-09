#!/usr/bin/env python3
import subprocess
import sys
import os
import time

backend_dir = r"D:\EOS\Eos final\eos-system\backend"
log_stdout_path = os.path.join(os.getenv("TEMP", "."), "uvicorn_stdout.log")
log_stderr_path = os.path.join(os.getenv("TEMP", "."), "uvicorn_stderr.log")

# Start uvicorn
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd=backend_dir,
    stdout=open(log_stdout_path, "w"),
    stderr=open(log_stderr_path, "w")
)

# Wait 5 seconds
time.sleep(5)

# Check if process is still running
if proc.poll() is None:
    print("Process still running after 5 seconds")
    # Read output files
    with open(log_stdout_path, "r") as f:
        stdout_data = f.read()
    with open(log_stderr_path, "r") as f:
        stderr_data = f.read()
    print("STDOUT length:", len(stdout_data))
    print("STDERR length:", len(stderr_data))
    print("STDERR preview:", stderr_data[:500] if stderr_data else "empty")
else:
    print("Process terminated with code:", proc.poll())
    with open(log_stdout_path, "r") as f:
        print("STDOUT:", f.read())
    with open(log_stderr_path, "r") as f:
        print("STDERR:", f.read())