import subprocess
import sys

# Change to backend directory
backend_dir = r"D:\EOS\Eos final\eos-system\backend"

# Start uvicorn capturing all output
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
    cwd=backend_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait a short time then check
import time
time.sleep(3)

# Check if process is still running
if proc.poll() is None:
    print("Process still running after 3 seconds")
    # Read some output
    output = proc.stdout.read(2000)
    stderr = proc.stderr.read(2000)
    print("STDOUT (first 2000 chars):", output)
    print("STDERR (first 2000 chars):", stderr)
    
    # Wait another 5 seconds
    time.sleep(5)
    
    # Check again
    if proc.poll() is None:
        print("Process still running after 8 seconds total")
    else:
        print("Process terminated")
        print("Final STDOUT:", proc.stdout.read())
        print("Final STDERR:", proc.stderr.read())
else:
    print("Process already terminated")
    print("STDOUT:", proc.stdout.read())
    print("STDERR:", proc.stderr.read())