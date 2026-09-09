import subprocess
import time
import sys
import httpx
import os

# Set env vars in THIS process too
os.environ['EOS_AUTH_MODE'] = 'production'
os.environ['EOS_SECRET_KEY'] = 'test-production-secret-key-for-verification'

env = os.environ.copy()
env['EOS_AUTH_MODE'] = 'production'
env['EOS_SECRET_KEY'] = 'test-production-secret-key-for-verification'

proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'main:app', '--port', '8008', '--host', '127.0.0.1'],
    cwd=r'D:\EOS\Eos final',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
)
time.sleep(4)

try:
    from core.production_auth import create_access_token
    
    # Create production token
    token = create_access_token(
        subject='user-123',
        extra_data={'tenant_id': 'tenant_a', 'email': 'prod@example.com', 'roles': ['admin']}
    )
    print('Production token created')
    
    # Test SCOPED read with production token
    r = httpx.get(
        'http://127.0.0.1:8008/api/v1/dynamic/entities/test_product/records',
        headers={'Authorization': 'Bearer ' + token},
        timeout=10
    )
    print('SCOPED READ with prod token: Status=' + str(r.status_code))
    if r.status_code == 200:
        data = r.json()
        print('  Count:', data.get('count'))
        print('  tenant_applied:', data.get('tenant_applied'))
        print('  effective_tenant:', data.get('effective_tenant'))
    
    # Test without token (should 401)
    r2 = httpx.get(
        'http://127.0.0.1:8008/api/v1/dynamic/entities/test_product/records',
        timeout=10
    )
    print('NO TOKEN: Status=' + str(r2.status_code))
    
    # Test with test token (should fail - wrong secret)
    from core.auth import create_test_token
    test_token = create_test_token('tenant_a')
    r3 = httpx.get(
        'http://127.0.0.1:8008/api/v1/dynamic/entities/test_product/records',
        headers={'Authorization': 'Bearer ' + test_token},
        timeout=10
    )
    print('TEST TOKEN (wrong secret): Status=' + str(r3.status_code))

except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
finally:
    proc.terminate()
    proc.wait()
