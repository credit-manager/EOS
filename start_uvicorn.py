import subprocess
import sys

# Change to the backend directory
backend_dir = r"D:\EOS\Eos final\eos-system\backend"
print("Starting server from: " + backend_dir)

# Start uvicorn server
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd=backend_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait a few seconds for startup
import time
time.sleep(3)

# Check if process is still running
if proc.poll() is None:
    print("Server started successfully with PID: " + str(proc.pid))
    print("Server is running in background")
else:
    print("Server failed to start")
    stdout = proc.stdout.read().decode('utf-8', errors='replace')
    stderr = proc.stderr.read().decode('utf-8', errors='replace')
    print("stdout: " + stdout)
    print("stderr: " + stderr)