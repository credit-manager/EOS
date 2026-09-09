import subprocess
import os

# Try local socket connection
env = os.environ.copy()
env['PGHOST'] = ''  # Local socket

result = subprocess.run(
    [r'C:\Program Files\PostgreSQL\18\bin\psql.exe', '-U', 'postgres', '-c', 'SELECT 1'],
    capture_output=True, text=True, timeout=10, env=env
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500] if result.stderr else "none")
print("Return code:", result.returncode)