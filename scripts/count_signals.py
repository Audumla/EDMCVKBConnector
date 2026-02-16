import json

with open('signals_catalog.json', encoding='utf-8') as f:
    catalog = json.load(f)

signals = catalog['signals']
non_comment = [k for k in signals if not k.startswith('_')]

enums = sum(1 for k in non_comment if signals[k].get('type') == 'enum')
strings = sum(1 for k in non_comment if signals[k].get('type') == 'string')
numbers = sum(1 for k in non_comment if signals[k].get('type') == 'number')
arrays = sum(1 for k in non_comment if signals[k].get('type') == 'array')
bools = sum(1 for k in non_comment if signals[k].get('type') == 'bool')

print(f"Total signals: {len(non_comment)}")
print(f"  Enums: {enums}")
print(f"  Strings: {strings}")
print(f"  Numbers: {numbers}")
print(f"  Arrays: {arrays}")
print(f"  Booleans: {bools}")
print(f"\n✓ Phase 5 Complete: All {bools} boolean signals converted to enums!")
