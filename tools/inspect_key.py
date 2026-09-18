
import json, urllib.request, re, time

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
KEY = os.path.join(ROOT, "research-logs", "training-approaches-key.json")
data = json.load(open(KEY))
print("key file type:", type(data).__name__)
if isinstance(data, list): print("n =", len(data)); print("sample keys:", list(data[0].keys()))
elif isinstance(data, dict): print("top keys:", list(data.keys())[:12])
print(json.dumps(data if isinstance(data, dict) else data[:1], indent=1)[:900])
