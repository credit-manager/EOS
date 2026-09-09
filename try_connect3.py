import subprocess
result = subprocess.run(
    ['C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe', '-U', 'postgres', '-c', "ALTER USER eos WITH PASSWORD 'Eos_2026_Secure';"],
    capture_output=True, text=True, timeout=10,
    env={**__import__('os').environ, 'PGHOST': r'.'}
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)