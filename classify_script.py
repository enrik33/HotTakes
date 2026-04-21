import urllib.request
import json
import time

base = "http://localhost:8000"

print("=== Starting classification loop ===")
total_classified = 0
total_gated = 0

for i in range(20):  # max 20 batches
    req = urllib.request.Request(
        f"{base}/api/admin/run/classify/sync", method="POST", data=b""
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
        print(f"Batch {i+1}: {result}")
        classified = result.get("result", {}).get("classified", 0)
        gated = result.get("result", {}).get("gated", 0)
        errors = result.get("result", {}).get("errors", 0)
        total_classified += classified
        total_gated += gated
        if classified + gated == 0:
            print("No more comments to classify!")
            break
    except Exception as e:
        print(f"Error on batch {i+1}: {e}")
        break
    time.sleep(2)

print(f"\nTotal classified: {total_classified}, gated: {total_gated}")

print("\n=== Running stats job ===")
req = urllib.request.Request(f"{base}/api/admin/run/stats", method="POST", data=b"")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(json.loads(resp.read()))
except Exception as e:
    print(f"Stats error: {e}")

time.sleep(3)

print("\n=== Running cluster job ===")
req = urllib.request.Request(f"{base}/api/admin/run/cluster", method="POST", data=b"")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(json.loads(resp.read()))
except Exception as e:
    print(f"Cluster error: {e}")

print("\nDone!")
