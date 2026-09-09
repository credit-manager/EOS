import subprocess, sys, time

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=r"D:\EOS\Eos final",
)
print(f"Server started, PID={proc.pid}")
print("Open http://127.0.0.1:8001/docs in your browser")
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
