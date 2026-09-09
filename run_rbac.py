import subprocess
import sys

# Run the RBAC test file
result = subprocess.run(
    [sys.executable, "-m", "pytest", "D:\\EOS\\Eos final\\eos-system\\backend\\app\\tests\\test_all_rbac.py", "-v", "--tb=long"],
    cwd="D:\\EOS\\Eos final\\eos-system\\backend",
    capture_output=True, text=True, timeout=60
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:1000] if result.stderr else "none")
print("Return code:", result.returncode)