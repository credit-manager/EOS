import subprocess, time
p = subprocess.Popen(['C:\\Program Files\\PostgreSQL\\18\\bin\\pg_ctl.exe', 'start', '-D', 'C:\\Program Files\\PostgreSQL\\18\\data'])
print('Started, PID:', p.pid)
time.sleep(5)
print('Waited 5 seconds')