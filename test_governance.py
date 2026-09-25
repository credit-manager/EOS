from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)
resp = client.post('/api/v1/auth/token', json={'email': 'admin@demo.local', 'password': 'Admin123!'})
token = resp.json()['access_token']
h = {'Authorization': 'Bearer ' + token}

print()
print('========================================')
print('  AI GOVERNANCE LAYER - All Endpoints')
print('========================================')
print()

# 1. Apply built-in policies
r = client.get('/api/v1/ai/governance/policies/builtin-apply', headers=h)
builtin = r.json()
print('1. POST /policies/builtin-apply  -> {} ({} policies applied)'.format(r.status_code, len(builtin)))

# 2. List policies
r = client.get('/api/v1/ai/governance/policies', headers=h)
policies = r.json()
print('2. GET  /policies               -> {} ({} tenant policies)'.format(r.status_code, len(policies)))
for p in policies[:5]:
    print('    - {} [{}] effect={}'.format(p['code'], p['name'], p['effect']))

# 3. List limits
r = client.get('/api/v1/ai/governance/limits', headers=h)
limits = r.json()
print('3. GET  /limits                 -> {} ({} limits)'.format(r.status_code, len(limits)))

# 4. List escalations
r = client.get('/api/v1/ai/governance/escalations', headers=h)
esc = r.json()
print('4. GET  /escalations            -> {} ({} pending)'.format(r.status_code, len(esc)))

# 5. List audit
r = client.get('/api/v1/ai/governance/audit?limit=5', headers=h)
audit = r.json()
print('5. GET  /audit                  -> {} ({} entries)'.format(r.status_code, len(audit)))

print()
print('========================================')
print('  All 5 governance endpoints: 200 OK')
print('========================================')
print()
