import urllib.request
import json

url = "http://localhost:8000/api/admin/run/classify/sync"
req = urllib.request.Request(url, method="POST", data=b"")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
        print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")
