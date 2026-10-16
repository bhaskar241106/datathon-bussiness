import urllib.request
import json

def test(url, method='GET', data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        req.add_header('Content-Type', 'application/json')
        body = json.dumps(data).encode('utf-8')
    else:
        body = None
    try:
        with urllib.request.urlopen(req, data=body, timeout=5) as res:
            print(f"{method} {url} -> Status {res.status}")
            if 'application/json' in res.headers.get('Content-Type', ''):
                payload = json.loads(res.read().decode('utf-8'))
                keys = list(payload.keys()) if isinstance(payload, dict) else len(payload)
                print(f"   Payload info: {keys}")
    except Exception as e:
        print(f"FAILED {url}: {e}")

if __name__ == '__main__':
    test('http://localhost:8000/')
    test('http://localhost:8000/api/overview')
    test('http://localhost:8000/api/margins')
    test('http://localhost:8000/api/returns')
    test('http://localhost:8000/api/inventory')
    test('http://localhost:8000/api/marketing')
    test('http://localhost:8000/api/customers')
    test('http://localhost:8000/api/action-cards')
    test('http://localhost:8000/api/sku-dossier/PR0192')
    test('http://localhost:8000/api/simulate', method='POST', data={'reprice_negative_skus': True, 'cap_discounts': True})
