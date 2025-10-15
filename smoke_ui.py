import requests
import time

BASE = 'http://localhost:8000'

def wait():
    for i in range(5):
        try:
            r = requests.get(BASE+'/', timeout=1)
            if r.status_code==200:
                return True
        except Exception:
            time.sleep(0.3)
    return False

if not wait():
    print('server not reachable')
    raise SystemExit(1)

print('calling /v1/demo')
r = requests.post(BASE+'/v1/demo', json={'prompt':'x','response':'As an AI, try https://fake.com'})
print(r.status_code, r.json())

print('calling /v1/check with demo key')
r = requests.post(BASE+'/v1/check', headers={'Authorization': 'Bearer df_demo_key_123'}, json={'prompt':'x','response':'As an AI, try https://fake.com'})
print(r.status_code, r.json())

print('calling /v1/export to get CSV')
r = requests.post(BASE+'/v1/export', headers={'Authorization': 'Bearer df_demo_key_123'}, json={'prompt':'x','response':'As an AI, try https://fake.com'})
print('export status', r.status_code)
print(r.text)
