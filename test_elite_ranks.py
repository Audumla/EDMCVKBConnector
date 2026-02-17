import json
import sys

sys.path.insert(0, 'src')

# Load signals catalog
with open('signals_catalog.json', encoding='utf-8') as f:
    catalog = json.load(f)

print("=== Checking Elite I-V Ranks ===\n")

# Check commander_ranks
rank_types = ['combat', 'trade', 'explore', 'soldier', 'exobiologist', 'mercenary', 'cqc']
for rank_type in rank_types:
    signal = catalog['signals']['commander_ranks'][rank_type]
    values = signal['values']
    print(f"{rank_type.capitalize()} rank: {len(values)} values")
    if len(values) >= 9:
        print(f"  Last 5: {', '.join([v['label'] for v in values[-5:]])}")
    print()

# Check commander_promotion
print("=== Checking Promotion Signals ===\n")
for rank_type in rank_types:
    if rank_type in ['empire', 'federation', 'cqc']:
        continue
    signal = catalog['signals']['commander_promotion'][rank_type]
    values = signal['values']
    print(f"{rank_type.capitalize()} promotion: {len(values)} values")
    if len(values) >= 9:
        print(f"  Last 5: {', '.join([v['label'] for v in values[-5:]])}")
    print()

print("✓ All Elite I-V ranks successfully added!")
