#!/usr/bin/env python3
"""
Validate that every enum value has a corresponding source mapping in derive field.
Ensures no orphaned values that can never be triggered by EDMC.
"""

import json
from pathlib import Path
from collections import defaultdict


def collect_enums(signals, path=""):
    """Recursively collect all enum signals"""
    enums = []
    
    for key, value in signals.items():
        if key.startswith('_comment'):
            continue
            
        if isinstance(value, dict):
            if value.get('type') == 'enum':
                full_key = f"{path}.{key}" if path else key
                enums.append({
                    'key': full_key,
                    'data': value,
                    'label': value.get('title', key),
                    'category': value.get('ui', {}).get('category', 'Unknown'),
                    'subcategory': value.get('ui', {}).get('subcategory', ''),
                    'values': value.get('values', []),
                    'derive': value.get('derive', {})
                })
            else:
                # Recurse for nested structures (e.g., commander_ranks.combat)
                full_key = f"{path}.{key}" if path else key
                enums.extend(collect_enums(value, full_key))
    
    return enums


def extract_mapped_values(derive):
    """Extract all values that can be produced by a derive operation"""
    mapped_values = set()
    
    if not derive:
        return mapped_values
    
    op = derive.get('op')
    
    # Handle map operations
    if op == 'map':
        derive_map = derive.get('map', {})
        # Add all mapped output values
        mapped_values.update(derive_map.values())
        
        # Add default if present
        if 'default' in derive and derive['default'] is not None:
            mapped_values.add(derive['default'])
    
    # Handle first_match operations
    elif op == 'first_match':
        cases = derive.get('cases', [])
        for case in cases:
            # Extract value from case
            case_value = case.get('value')
            if isinstance(case_value, dict):
                # Nested operation
                nested_values = extract_mapped_values(case_value)
                if nested_values is not None:
                    mapped_values.update(nested_values)
                else:
                    # Can't validate nested path/derive operations
                    return None
            elif case_value is not None:
                mapped_values.add(case_value)
        
        # Add default if present
        if 'default' in derive and derive['default'] is not None:
            mapped_values.add(derive['default'])
    
    # Handle path operations (direct value passthrough)
    elif op == 'path':
        # Path operations pass through raw values, can't validate without knowing EDMC schema
        return None  # Special marker: validation not applicable
    
    # Handle derive operations (complex multi-source)
    elif op == 'derive':
        # Complex derived signals - can't easily validate
        return None
    
    return mapped_values


def validate_enum_values():
    """Check that all enum values have source mappings"""
    
    catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    enums = collect_enums(catalog['signals'])
    
    print("=" * 80)
    print("ENUM VALUE MAPPING VALIDATION")
    print("=" * 80)
    print(f"\nAnalyzing {len(enums)} enum signals...\n")
    
    issues = []
    validated = 0
    skipped = 0
    
    for enum in enums:
        key = enum['key']
        defined_values = set()
        
        # Extract defined values from values array
        for val_def in enum['values']:
            val = val_def.get('value')
            if val is not None:
                # Normalize to string for comparison
                defined_values.add(str(val))
        
        # Extract mapped values from derive
        mapped_values = extract_mapped_values(enum['derive'])
        
        if mapped_values is None:
            # Validation not applicable (path/derive operations)
            skipped += 1
            continue
        
        # Normalize mapped values to strings
        mapped_values = {str(v) for v in mapped_values}
        
        # Find unmapped values (defined but not mapped)
        unmapped = defined_values - mapped_values
        
        # Find extra mappings (mapped but not defined)
        extra = mapped_values - defined_values
        
        if unmapped or extra:
            issues.append({
                'key': key,
                'label': enum['label'],
                'category': enum['category'],
                'subcategory': enum['subcategory'],
                'unmapped': unmapped,
                'extra': extra,
                'defined_values': defined_values,
                'mapped_values': mapped_values,
                'derive': enum['derive']
            })
        else:
            validated += 1
    
    # Report results
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total enums: {len(enums)}")
    print(f"[OK] Validated (all values mapped): {validated}")
    print(f"[SKIP] Skipped (validation not applicable): {skipped}")
    print(f"[X] Issues found: {len(issues)}")
    
    if issues:
        print("\n" + "=" * 80)
        print("ENUM VALUES WITH MAPPING ISSUES")
        print("=" * 80)
        
        # Group by issue type
        unmapped_only = [i for i in issues if i['unmapped'] and not i['extra']]
        extra_only = [i for i in issues if i['extra'] and not i['unmapped']]
        both = [i for i in issues if i['unmapped'] and i['extra']]
        
        if unmapped_only:
            print(f"\n[X] UNMAPPED VALUES ({len(unmapped_only)} enums)")
            print("    These values are defined but have no source mapping (can never be triggered):\n")
            for issue in unmapped_only:
                print(f"• {issue['key']}")
                print(f"  Label: {issue['label']}")
                print(f"  Category: {issue['category']}")
                if issue['subcategory']:
                    print(f"  Subcategory: {issue['subcategory']}")
                print(f"  Unmapped values: {', '.join(sorted(issue['unmapped']))}")
                print()
        
        if extra_only:
            print(f"\n[!] EXTRA MAPPINGS ({len(extra_only)} enums)")
            print("    These derive mappings produce values not defined in values array:\n")
            for issue in extra_only:
                print(f"• {issue['key']}")
                print(f"  Label: {issue['label']}")
                print(f"  Category: {issue['category']}")
                if issue['subcategory']:
                    print(f"  Subcategory: {issue['subcategory']}")
                print(f"  Extra mappings: {', '.join(sorted(issue['extra']))}")
                print()
        
        if both:
            print(f"\n[X] BOTH ISSUES ({len(both)} enums)")
            print("    These have both unmapped values and extra mappings:\n")
            for issue in both:
                print(f"• {issue['key']}")
                print(f"  Label: {issue['label']}")
                print(f"  Category: {issue['category']}")
                if issue['subcategory']:
                    print(f"  Subcategory: {issue['subcategory']}")
                print(f"  Unmapped values: {', '.join(sorted(issue['unmapped']))}")
                print(f"  Extra mappings: {', '.join(sorted(issue['extra']))}")
                print(f"  Derive operation: {issue['derive'].get('op', 'unknown')}")
                print()
    else:
        print("\n[OK] All validated enums have complete value mappings!")
        print("     Every defined value can be triggered by EDMC data")


if __name__ == '__main__':
    validate_enum_values()
