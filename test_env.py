import subprocess
import time
import sys
import os

env = os.environ.copy()
env['EOS_AUTH_MODE'] = 'production'
env['EOS_SECRET_KEY'] = 'test123'

proc = subprocess.Popen(
    [sys.executable, '-c', 'import os; print(os.getenv("EOS_AUTH_MODE"), os.getenv("EOS_SECRET_KEY"))'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
)
stdout, stderr = proc.communicate()
print('Output:', stdout.decode().strip())
