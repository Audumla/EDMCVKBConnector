import json
import sys

try:
    with open('signals_catalog.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Valid JSON with {len(data.get('signals', {}))} signals")
    sys.exit(0)
except json.JSONDecodeError as e:
    print(f"JSON Error: {e}")
    sys.exit(1)
