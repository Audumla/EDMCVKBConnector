#!/usr/bin/env python3
"""
Analyze enum signals in signals_catalog.json for completeness and validity
"""

import json
from pathlib import Path
from collections import defaultdict


def analyze_enums():
    """Analyze all enum signals in the catalog"""
    
    catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    enums = []
    
    def collect_enums(obj, prefix=""):
        """Recursively collect all enum signals"""
        if isinstance(obj, dict):
            # Check if this is an enum signal
            if obj.get('type') == 'enum' and 'ui' in obj:
                key = prefix
                enums.append({
                    'key': key,
                    'label': obj.get('ui', {}).get('label', ''),
                    'category': obj.get('ui', {}).get('category', ''),
                    'subcategory': obj.get('ui', {}).get('subcategory', ''),
                    'derive': obj.get('derive'),
                    'values': obj.get('values', []),
                    'merged_from': obj.get('_merged_from'),
                    'merged_into': obj.get('_merged_into'),
                    'title': obj.get('title', '')
                })
            # Check nested signals
            elif 'ui' not in obj and 'type' not in obj:
                for key, value in obj.items():
                    if not key.startswith('_comment'):
                        new_prefix = f"{prefix}.{key}" if prefix else key
                        collect_enums(value, new_prefix)
    
    # Collect all enum signals
    for key, value in catalog['signals'].items():
        if not key.startswith('_comment'):
            collect_enums(value, key)
    
    print("=" * 80)
    print("ENUM SIGNAL ANALYSIS")
    print("=" * 80)
    print(f"\nTotal enum signals found: {len(enums)}")
    
    # Categorize by completeness
    complete = []
    missing_derive = []
    missing_values = []
    has_merge_metadata = []
    invalid_paths = []
    
    for enum in enums:
        is_complete = True
        
        # Check for merge metadata
        if enum['merged_from'] or enum['merged_into']:
            has_merge_metadata.append(enum)
        
        # Check derive field
        if not enum['derive']:
            missing_derive.append(enum)
            is_complete = False
        else:
            # Validate derive path - handle both direct path and nested map/from structure
            derive = enum['derive']
            path = derive.get('path', '')
            
            # Check if it's a map operation with nested source
            if not path and derive.get('op') == 'map' and isinstance(derive.get('from'), dict):
                nested_from = derive['from']
                path = nested_from.get('path', '')
                
                # Handle flag operations in nested structure
                if not path and nested_from.get('op') == 'flag':
                    field_ref = nested_from.get('field_ref', '')
                    if field_ref == 'ship_flags':
                        path = 'dashboard.Flags'
                    elif field_ref == 'foot_flags':
                        path = 'dashboard.Flags2'
                    elif field_ref:
                        path = f'field_ref.{field_ref}'
            
            # Check if it's a derive operation (multi-source derived signal)
            if not path and derive.get('op') == 'derive':
                # Derived signals are valid but don't have a single source path
                path = 'derived'
            
            # Check if it's a first_match operation (complex conditional logic)
            if not path and derive.get('op') == 'first_match':
                # This is a complex derived signal with conditional cases
                path = 'derived'
            
            # Check if it's a flag operation (direct, not nested)
            if not path and derive.get('op') == 'flag':
                field_ref = derive.get('field_ref', '')
                if field_ref == 'ship_flags':
                    path = 'dashboard.Flags'
                elif field_ref == 'foot_flags':
                    path = 'dashboard.Flags2'
                elif field_ref:
                    path = f'field_ref.{field_ref}'
            
            # Check if it's a journal event
            if not path and derive.get('op') in ['journal_event', 'journal']:
                path = f"journal.{derive.get('event', 'unknown')}"
            
            # Check if it's a bitfield
            if not path and derive.get('op') == 'bitfield':
                path = derive.get('path', '')
            
            if path:
                # Validate the path
                valid_prefixes = ['dashboard.', 'state.', 'journal.', 'capi.', 'derived']
                if not any(path.startswith(prefix) or path == 'derived' for prefix in valid_prefixes):
                    invalid_paths.append(enum)
                    is_complete = False
            else:
                missing_derive.append(enum)
                is_complete = False
        
        #Check values
        if not enum['values']:
            missing_values.append(enum)
            is_complete = False
        
        if is_complete:
            complete.append(enum)
    
    print(f"[OK] Complete (has derive + values + valid path): {len(complete)}")
    print(f"[X] Missing derive field: {len(missing_derive)}")
    print(f"[!]  Invalid/unrecognized path: {len(invalid_paths)}")
    print(f"[!]  Missing values: {len(missing_values)}")
    print(f"[#] Has merge metadata: {len(has_merge_metadata)}")
    
    # Group by source
    print("\n" + "=" * 80)
    print("ENUMS BY SOURCE EVENT")
    print("=" * 80)
    
    by_source = defaultdict(list)
    for enum in complete:
        derive = enum['derive']
        path = derive.get('path', '')
        
        # Handle nested map/from structure
        if not path and derive.get('op') == 'map' and isinstance(derive.get('from'), dict):
            path = derive['from'].get('path', '')
        
        # Handle derived signals
        if not path and derive.get('op') == 'derive':
            path = 'derived'
        
        # Handle journal events
        if not path and derive.get('op') in ['journal_event', 'journal']:
            path = f"journal.{derive.get('event', 'unknown')}"
        
        # Handle bitfield
        if not path and derive.get('op') == 'bitfield':
            path = derive.get('path', '')
        
        # Categorize by source
        if path.startswith('dashboard.'):
            by_source['dashboard'].append(enum)
        elif path.startswith('state.'):
            by_source['state'].append(enum)
        elif path.startswith('journal.'):
            by_source['journal'].append(enum)
        elif path.startswith('capi.'):
            by_source['capi'].append(enum)
        elif path == 'derived':
            by_source['derived'].append(enum)
        else:
            by_source['other'].append(enum)
    
    for source in ['dashboard', 'state', 'journal', 'capi', 'derived', 'other']:
        if source in by_source:
            print(f"\n{source.upper()}: {len(by_source[source])} enums")
            for enum in sorted(by_source[source], key=lambda x: x['key'])[:5]:
                derive = enum['derive']
                path = derive.get('path', '')
                if not path and derive.get('op') == 'map' and isinstance(derive.get('from'), dict):
                    path = derive['from'].get('path', '')
                if not path and derive.get('op') == 'derive':
                    path = 'derived (multi-source)'
                if not path and derive.get('op') in ['journal_event', 'journal']:
                    path = f"journal.{derive.get('event', '*')}"
                if not path and derive.get('op') == 'bitfield':
                    path = derive.get('path', '') + f" [bit {derive.get('bit', '?')}]"
                print(f"  • {enum['key']:<40} -> {path}")
            if len(by_source[source]) > 5:
                print(f"  ... and {len(by_source[source]) - 5} more")
    
    # Group by category
    print("\n" + "=" * 80)
    print("ENUMS BY CATEGORY")
    print("=" * 80)
    
    by_category = defaultdict(list)
    for enum in enums:
        category = enum['category'] or 'Uncategorized'
        by_category[category].append(enum)
    
    for category in sorted(by_category.keys(), key=lambda x: len(by_category[x]), reverse=True)[:10]:
        print(f"{category}: {len(by_category[category])} enums")
    
    # Report problems
    if missing_derive:
        print("\n" + "=" * 80)
        print("[!]  ENUMS MISSING DERIVE (SOURCE EVENT)")
        print("=" * 80)
        for enum in missing_derive:
            print(f"\n• {enum['key']}")
            print(f"  Label: {enum['label']}")
            print(f"  Category: {enum['category']}")
            if enum['subcategory']:
                print(f"  Subcategory: {enum['subcategory']}")
            print(f"  Values: {len(enum['values'])} items")
            if enum['merged_from']:
                print(f"  [!]  Has merge metadata - can be recovered!")
            if enum['merged_into']:
                print(f"  ℹ️  Was merged into: {enum['merged_into']}")
    
    if invalid_paths:
        print("\n" + "=" * 80)
        print("[!]  ENUMS WITH INVALID PATHS")
        print("=" * 80)
        for enum in invalid_paths:
            path = enum['derive'].get('path', '')
            print(f"• {enum['key']}: {path}")
    
    if missing_values:
        print("\n" + "=" * 80)
        print("[!]  ENUMS MISSING VALUES")
        print("=" * 80)
        for enum in missing_values:
            print(f"• {enum['key']}")
            print(f"  Label: {enum['label']}")
            print(f"  Category: {enum['category']}")
            if enum['subcategory']:
                print(f"  Subcategory: {enum['subcategory']}")
    
    if has_merge_metadata:
        print("\n" + "=" * 80)
        print("[#] ENUMS WITH MERGE METADATA")
        print("=" * 80)
        for enum in has_merge_metadata:
            print(f"\n• {enum['key']}")
            if enum['merged_from']:
                print(f"  Merged from: {len(enum['merged_from'])} source(s)")
                for merge in enum['merged_from']:
                    print(f"    - {merge.get('source_key')}: {merge.get('derive', {}).get('path')}")
            if enum['merged_into']:
                print(f"  Merged into: {enum['merged_into']}")
    
    # Propose fixes
    if missing_derive or invalid_paths:
        print("\n" + "=" * 80)
        print("PROPOSED FIXES")
        print("=" * 80)
        print("\nBased on signal names and categories, here are proposed derive paths:")
        print("(These should be reviewed before applying)\n")
        
        fixes = []
        for enum in missing_derive + invalid_paths:
            proposed_path = propose_derive_path(enum)
            if proposed_path:
                fixes.append({
                    'key': enum['key'],
                    'current_path': enum['derive'].get('path') if enum['derive'] else None,
                    'proposed_path': proposed_path,
                    'confidence': 'high' if proposed_path['confidence'] > 0.8 else 'medium' if proposed_path['confidence'] > 0.5 else 'low'
                })
        
        for fix in fixes:
            print(f"• {fix['key']}")
            if fix['current_path']:
                print(f"  Current: {fix['current_path']}")
            print(f"  Proposed: {fix['proposed_path']['path']} (confidence: {fix['confidence']})")
            print(f"  Reason: {fix['proposed_path']['reason']}")
            print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if not missing_derive and not invalid_paths:
        print("[OK] All enum signals are COMPLETE and VALID!")
        print("   All enums have source event information (derive field)")
        print("   All paths point to valid EDMC data sources")
    else:
        print(f"[!]  Found {len(missing_derive) + len(invalid_paths)} enum(s) needing attention")
        print("   Use the catalog editor's 'Check Enum Completeness' feature to fix")


def propose_derive_path(enum):
    """Propose a derive path based on enum characteristics"""
    key = enum['key']
    category = enum['category']
    subcategory = enum['subcategory']
    label = enum['label']
    
    proposals = []
    
    # Check for rank-related enums
    if 'rank' in key.lower() or 'rank' in subcategory.lower():
        if 'combat' in key.lower():
            proposals.append({'path': 'state.Rank.Combat', 'confidence': 0.9, 'reason': 'Rank-related, combat keyword'})
        elif 'trade' in key.lower():
            proposals.append({'path': 'state.Rank.Trade', 'confidence': 0.9, 'reason': 'Rank-related, trade keyword'})
        elif 'explore' in key.lower() or 'exploration' in key.lower():
            proposals.append({'path': 'state.Rank.Explore', 'confidence': 0.9, 'reason': 'Rank-related, exploration keyword'})
        elif 'empire' in key.lower():
            proposals.append({'path': 'state.Rank.Empire', 'confidence': 0.9, 'reason': 'Rank-related, empire keyword'})
        elif 'federation' in key.lower() or 'fed' in key.lower():
            proposals.append({'path': 'state.Rank.Federation', 'confidence': 0.9, 'reason': 'Rank-related, federation keyword'})
    
    # Check for GUI-related enums
    if 'gui' in key.lower() or 'focus' in key.lower():
        proposals.append({'path': 'dashboard.GuiFocus', 'confidence': 0.85, 'reason': 'GUI/focus keyword'})
    
    # Check for vehicle/mode enums
    if 'vehicle' in key.lower() or category == 'Ship':
        if 'type' in key.lower():
            proposals.append({'path': 'dashboard.Vehicle', 'confidence': 0.8, 'reason': 'Vehicle type indicator'})
    
    # Check merge metadata
    if enum.get('merged_from'):
        for merge in enum['merged_from']:
            derive = merge.get('derive', {})
            if derive.get('path'):
                proposals.append({'path': derive['path'], 'confidence': 0.95, 'reason': f"Recovered from merge metadata (source: {merge.get('source_key')})"})
    
    # Return best proposal
    if proposals:
        return max(proposals, key=lambda x: x['confidence'])
    
    return None


if __name__ == '__main__':
    analyze_enums()

