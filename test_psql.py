import subprocess
result = subprocess.run(
    [r'C:\Program Files\PostgreSQL\18\bin\psql.exe', '-U', 'postgres', '-h', 'localhost', '-c', 'SELECT 1'],
    capture_output=True, text=True, timeout=10
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)