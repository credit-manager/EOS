import subprocess
import os

# Try connecting via local socket - PGHOST set to empty/local
env = os.environ.copy()
env['PGHOST'] = ''  # Try local socket

result = subprocess.run(
    [r'C:\Program Files\PostgreSQL\18\bin\psql.exe', '-U', 'postgres', '-c', "ALTER USER eos WITH PASSWORD 'Eos_2026_Secure';"],
    capture_output=True, text=True, timeout=10, env=env
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500] if result.stderr else "none")
print("Return code:", result.returncode)