import uvicorn
import sys
import os

# Add the backend directory to path
sys.path.insert(0, r"D:\EOS\Eos final\eos-system\backend")

try:
    os.chdir(r"D:\EOS\Eos final\eos-system\backend")
    server = uvicorn.run("app.main:app", host="0.0.0.0", port=8001, log_level="info")
    print("Server started successfully on port 8001")
except Exception as e:
    print(f"Error starting server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)