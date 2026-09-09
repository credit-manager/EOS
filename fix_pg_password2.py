import subprocess
import sys

# Try to alter the eos user password using psql
result = subprocess.run([
    r'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    '-U', 'postgres',
    '-c', 'ALTER USER eos WITH PASSWORD \"0100\"'
], capture_output=True, text=True, timeout=10)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500] if result.stderr else "none")
print("Return code:", result.returncode)