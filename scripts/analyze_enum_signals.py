#!/usr/bin/env python3
"""
Comprehensive analysis of enum signals in signals_catalog.json
Identifies missing/invalid EDMC source event information
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

def load_catalog(catalog_path: Path) -> dict:
    """Load the signals catalog."""
    with open(catalog_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_bitfield_mapping(catalog: dict) -> Dict[str, str]:
    """Extract bitfield references mapping (e.g., ship_flags -> dashboard.Flags)."""
    return catalog.get("bitfields", {})

def extract_all_signals(catalog: dict, parent_key: str = "") -> List[Tuple[str, dict]]:
    """
    Recursively extract all signals from the catalog.
    Returns list of (full_path, signal_data) tuples.
    """
    signals = []
    
    for key, value in catalog.items():
        if key.startswith("_"):
            continue
            
        full_path = f"{parent_key}.{key}" if parent_key else key
        
        if isinstance(value, dict):
            # Check if this is a signal definition
            if "type" in value:
                signals.append((full_path, value))
            # Recurse into nested structures
            else:
                signals.extend(extract_all_signals(value, full_path))
    
    return signals

def extract_path_from_derive(derive: dict, bitfields: Dict[str, str] = None) -> Tuple[str, str]:
    """
    Extract the source path from a derive structure.
    Handles different derive operation types.
    Returns (path, derive_type) where derive_type is "path", "flag", "sources", etc.
    """
    if not derive:
        return None, None
    
    # Case 1: Simple path operation
    if derive.get("op") == "path" and "path" in derive:
        return derive["path"], "path"
    
    # Case 2: Map operation with nested from.path
    if derive.get("op") == "map" and "from" in derive:
        from_op = derive["from"]
        if isinstance(from_op, dict):
            # Check if from uses path
            if "path" in from_op:
                return from_op["path"], "map_path"
            # Check if from uses flag operation
            if from_op.get("op") == "flag" and "field_ref" in from_op:
                field_ref = from_op["field_ref"]
                # Resolve field_ref to actual path if bitfields mapping available
                if bitfields and field_ref in bitfields:
                    return bitfields[field_ref], "flag"
                return field_ref, "flag"
    
    # Case 3: Check for sources - alternative derive method
    if "sources" in derive:
        # This is an older/alternative format
        primary = derive.get("sources", {}).get("primary")
        if primary:
            primary_source = derive["sources"].get(primary, {})
            if "path" in primary_source:
                return primary_source["path"], "sources"
    
    # Case 4: Other operations - check common locations
    if "path" in derive:
        return derive["path"], "unknown"
    
    return None, None

def is_valid_derive_path(derive: dict, bitfields: Dict[str, str] = None) -> Tuple[bool, str]:
    """
    Check if a derive path is valid.
    Returns (is_valid, reason)
    """
    if not derive:
        return False, "No derive field"
    
    # Extract path from various derive structures
    path, derive_type = extract_path_from_derive(derive, bitfields)
    
    if not path:
        return False, "No path found in derive structure"
    
    # Check if path starts with valid source
    valid_sources = ["dashboard", "state", "journal", "capi"]
    
    if not any(path.startswith(source) for source in valid_sources):
        return False, f"Path doesn't start with valid source: {path} (type: {derive_type})"
    
    # Check for suspicious patterns
    if ".." in path:
        return False, "Path contains '..' (suspicious)"
    
    if path.endswith("."):
        return False, "Path ends with '.'"
    
    return True, f"Valid ({derive_type})"

def categorize_enum_signal(signal_path: str, signal_data: dict, bitfields: Dict[str, str] = None) -> Tuple[str, dict]:
    """
    Categorize an enum signal and return category with metadata.
    Returns (category, metadata_dict)
    """
    metadata = {
        "path": signal_path,
        "has_derive": "derive" in signal_data,
        "has_values": "values" in signal_data and len(signal_data.get("values", [])) > 0,
        "has_merged_into": "_merged_into" in signal_data,
        "has_merged_from": "_merged_from" in signal_data,
        "category": signal_data.get("category", signal_data.get("ui", {}).get("category", "unknown")),
        "subcategory": signal_data.get("subcategory", signal_data.get("ui", {}).get("subcategory", "")),
        "description": signal_data.get("description", signal_data.get("ui", {}).get("label", "")),
        "derive": signal_data.get("derive"),
        "derive_path": None,
        "derive_type": None,
    }
    
    # Extract the actual path from derive
    if metadata["has_derive"]:
        path, derive_type = extract_path_from_derive(signal_data["derive"], bitfields)
        metadata["derive_path"] = path
        metadata["derive_type"] = derive_type
    
    # Check derive validity if present
    if metadata["has_derive"]:
        is_valid, reason = is_valid_derive_path(signal_data["derive"], bitfields)
        metadata["derive_valid"] = is_valid
        metadata["derive_reason"] = reason
    else:
        metadata["derive_valid"] = False
        metadata["derive_reason"] = "No derive field"
    
    # Categorize
    if metadata["has_merged_into"]:
        return "HAS_MERGED_INTO", metadata
    
    if metadata["has_merged_from"]:
        return "HAS_MERGED_FROM", metadata
    
    if not metadata["has_derive"]:
        if metadata["has_values"]:
            return "MISSING_DERIVE", metadata
        else:
            return "MISSING_DERIVE_AND_VALUES", metadata
    
    if not metadata["derive_valid"]:
        return "INVALID_PATH", metadata
    
    if not metadata["has_values"]:
        return "EMPTY_VALUES", metadata
    
    return "COMPLETE", metadata

def infer_derive_path(signal_path: str, signal_data: dict, all_signals: List[Tuple[str, dict]]) -> Tuple[str, str, float]:
    """
    Attempt to infer the correct derive path for a signal.
    Returns (suggested_path, reasoning, confidence_score)
    confidence_score: 0.0-1.0
    """
    signal_name = signal_path.split(".")[-1]
    category = signal_data.get("category", "")
    subcategory = signal_data.get("subcategory", "")
    description = signal_data.get("description", "")
    
    # Check for merge metadata hints
    if "_merged_from" in signal_data:
        merged_from = signal_data["_merged_from"]
        return "", f"Has _merged_from: {merged_from} - needs manual review", 0.3
    
    # Pattern matching based on signal name
    name_lower = signal_name.lower()
    
    # GuiFocus pattern
    if name_lower == "guifocus":
        return "dashboard.GuiFocus", "Standard dashboard GuiFocus field", 0.95
    
    # Rank patterns
    if name_lower.startswith("rank"):
        rank_type = signal_name.replace("Rank", "")
        return f"state.Rank.{rank_type}", f"Standard rank path for {rank_type}", 0.9
    
    # Combat Rank specific
    if "combat" in name_lower and "rank" in name_lower:
        return "state.Rank.Combat", "Combat rank from state", 0.9
    
    # Trade Rank
    if "trade" in name_lower and "rank" in name_lower:
        return "state.Rank.Trade", "Trade rank from state", 0.9
    
    # Explore Rank
    if ("explore" in name_lower or "exploration" in name_lower) and "rank" in name_lower:
        return "state.Rank.Explore", "Exploration rank from state", 0.9
    
    # Empire Rank
    if "empire" in name_lower and "rank" in name_lower:
        return "state.Rank.Empire", "Empire rank from state", 0.9
    
    # Federation Rank
    if ("federation" in name_lower or "federal" in name_lower) and "rank" in name_lower:
        return "state.Rank.Federation", "Federation rank from state", 0.9
    
    # CQC Rank
    if "cqc" in name_lower and "rank" in name_lower:
        return "state.Rank.CQC", "CQC rank from state", 0.9
    
    # Soldier Rank (Odyssey)
    if "soldier" in name_lower and "rank" in name_lower:
        return "state.Rank.Soldier", "Soldier rank from state (Odyssey)", 0.9
    
    # Exobiologist Rank (Odyssey)
    if "exobiologist" in name_lower and "rank" in name_lower:
        return "state.Rank.Exobiologist", "Exobiologist rank from state (Odyssey)", 0.9
    
    # Mercenary Rank (Odyssey)
    if "mercenary" in name_lower and "rank" in name_lower:
        return "state.Rank.Mercenary", "Mercenary rank from state (Odyssey)", 0.9
    
    # LegalState patterns
    if "legalstate" in name_lower or "legal_state" in name_lower:
        return "dashboard.LegalState", "Dashboard LegalState field", 0.85
    
    # Firegroup patterns
    if "firegroup" in name_lower:
        return "dashboard.FireGroup", "Dashboard FireGroup field", 0.85
    
    # Fuel patterns
    if name_lower == "fuelmain" or name_lower == "fuel_main":
        return "dashboard.Fuel.FuelMain", "Dashboard Fuel.FuelMain", 0.85
    
    if name_lower == "fuelreservoir" or name_lower == "fuel_reservoir":
        return "dashboard.Fuel.FuelReservoir", "Dashboard Fuel.FuelReservoir", 0.85
    
    # Vehicle patterns
    if "vehicle" in name_lower:
        # Check if it's about status/mode
        if "mode" in description.lower() or "type" in description.lower():
            return "dashboard.Vehicle", "Dashboard Vehicle field", 0.8
    
    # Check for similar named signals that have derive
    similar_signals = []
    for other_path, other_data in all_signals:
        if other_data.get("type") == "enum" and "derive" in other_data:
            other_name = other_path.split(".")[-1]
            # Simple similarity check
            if other_name.lower() == name_lower:
                similar_signals.append((other_path, other_data))
    
    if similar_signals:
        # Use the derive from a similar signal
        derive = similar_signals[0][1]["derive"]
        return derive.get("path", ""), f"Found similar signal: {similar_signals[0][0]}", 0.7
    
    # Check category-based patterns
    if category == "ship" or category == "vehicle":
        if subcategory == "status":
            return "", f"Category: {category}/{subcategory} - likely dashboard field, needs manual review", 0.4
        if subcategory == "combat":
            return "", f"Category: {category}/{subcategory} - likely dashboard or journal, needs manual review", 0.3
    
    if category == "commander":
        if "rank" in subcategory.lower():
            return "", f"Category: commander/ranks - likely state.Rank field, needs manual review", 0.5
    
    # Default: Can't infer
    return "", f"Unable to infer from name '{signal_name}', category '{category}/{subcategory}'", 0.0

def generate_report(categories: Dict[str, List[dict]], all_signals: List[Tuple[str, dict]]) -> str:
    """Generate a comprehensive report."""
    
    lines = []
    lines.append("=" * 80)
    lines.append("ENUM SIGNALS ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Summary statistics
    total_enums = sum(len(sigs) for sigs in categories.values())
    lines.append("SUMMARY STATISTICS")
    lines.append("-" * 80)
    lines.append(f"Total enum signals: {total_enums}")
    lines.append("")
    
    for cat_name, signals in sorted(categories.items()):
        lines.append(f"  {cat_name}: {len(signals)}")
    lines.append("")
    
    # Detailed breakdown for each category
    priority_order = [
        "MISSING_DERIVE",
        "MISSING_DERIVE_AND_VALUES",
        "INVALID_PATH",
        "EMPTY_VALUES",
        "HAS_MERGED_INTO",
        "HAS_MERGED_FROM",
        "COMPLETE"
    ]
    
    for cat_name in priority_order:
        if cat_name not in categories or not categories[cat_name]:
            continue
        
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"CATEGORY: {cat_name}")
        lines.append("=" * 80)
        lines.append(f"Count: {len(categories[cat_name])}")
        lines.append("")
        
        for i, metadata in enumerate(categories[cat_name], 1):
            lines.append(f"{i}. {metadata['path']}")
            lines.append(f"   Category: {metadata['category']} / {metadata['subcategory']}")
            
            if metadata['description']:
                desc = metadata['description'][:100]
                if len(metadata['description']) > 100:
                    desc += "..."
                lines.append(f"   Description: {desc}")
            
            if metadata['has_derive']:
                derive_path = metadata.get('derive_path', 'N/A')
                lines.append(f"   Current derive path: {derive_path}")
                lines.append(f"   Derive valid: {metadata['derive_valid']} - {metadata['derive_reason']}")
            
            if metadata['has_merged_into']:
                lines.append(f"   MERGED INTO: {metadata.get('_merged_into', 'N/A')}")
            
            if metadata['has_merged_from']:
                lines.append(f"   MERGED FROM: {metadata.get('_merged_from', 'N/A')}")
            
            # Try to infer for missing/invalid
            if cat_name in ["MISSING_DERIVE", "MISSING_DERIVE_AND_VALUES", "INVALID_PATH"]:
                # Find the original signal data
                signal_data = None
                for sig_path, sig_data in all_signals:
                    if sig_path == metadata['path']:
                        signal_data = sig_data
                        break
                
                if signal_data:
                    suggested_path, reasoning, confidence = infer_derive_path(
                        metadata['path'], signal_data, all_signals
                    )
                    
                    lines.append(f"   INFERENCE:")
                    lines.append(f"     Suggested path: {suggested_path if suggested_path else 'NEEDS_MANUAL_REVIEW'}")
                    lines.append(f"     Reasoning: {reasoning}")
                    lines.append(f"     Confidence: {confidence:.2f}")
            
            lines.append("")
    
    return "\n".join(lines)

def generate_fixes_json(categories: Dict[str, List[dict]], all_signals: List[Tuple[str, dict]]) -> dict:
    """Generate suggested fixes in JSON format."""
    
    fixes = {
        "high_confidence_fixes": [],
        "medium_confidence_fixes": [],
        "needs_manual_review": [],
        "merge_metadata_signals": []
    }
    
    for cat_name in ["MISSING_DERIVE", "INVALID_PATH"]:
        if cat_name not in categories:
            continue
        
        for metadata in categories[cat_name]:
            # Find the original signal data
            signal_data = None
            for sig_path, sig_data in all_signals:
                if sig_path == metadata['path']:
                    signal_data = sig_data
                    break
            
            if not signal_data:
                continue
            
            suggested_path, reasoning, confidence = infer_derive_path(
                metadata['path'], signal_data, all_signals
            )
            
            fix_entry = {
                "signal_path": metadata['path'],
                "current_derive_path": metadata.get('derive_path'),
                "suggested_derive_path": suggested_path,
                "reasoning": reasoning,
                "confidence": confidence,
                "category": metadata['category'],
                "subcategory": metadata['subcategory']
            }
            
            if confidence >= 0.8:
                fixes["high_confidence_fixes"].append(fix_entry)
            elif confidence >= 0.5:
                fixes["medium_confidence_fixes"].append(fix_entry)
            else:
                fixes["needs_manual_review"].append(fix_entry)
    
    # Add merge metadata signals
    for cat_name in ["HAS_MERGED_INTO", "HAS_MERGED_FROM"]:
        if cat_name not in categories:
            continue
        
        for metadata in categories[cat_name]:
            signal_data = None
            for sig_path, sig_data in all_signals:
                if sig_path == metadata['path']:
                    signal_data = sig_data
                    break
            
            if signal_data:
                fixes["merge_metadata_signals"].append({
                    "signal_path": metadata['path'],
                    "merge_type": cat_name,
                    "merge_target": signal_data.get("_merged_into") or signal_data.get("_merged_from"),
                    "has_derive": metadata['has_derive'],
                    "has_values": metadata['has_values']
                })
    
    return fixes

def main():
    """Main analysis function."""
    
    # Load catalog
    catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
    print(f"Loading catalog from: {catalog_path}")
    
    catalog = load_catalog(catalog_path)
    
    # Extract all signals
    print("Extracting all signals...")
    all_signals = extract_all_signals(catalog)
    print(f"Found {len(all_signals)} total signals")
    
    # Filter enum signals
    enum_signals = [(path, data) for path, data in all_signals if data.get("type") == "enum"]
    print(f"Found {len(enum_signals)} enum signals")
    
    # Categorize enum signals
    print("Categorizing enum signals...")
    categories = defaultdict(list)
    
    for signal_path, signal_data in enum_signals:
        category, metadata = categorize_enum_signal(signal_path, signal_data)
        categories[category].append(metadata)
    
    # Generate report
    print("\nGenerating report...")
    report = generate_report(dict(categories), all_signals)
    
    # Save report
    report_path = Path(__file__).parent.parent / "enum_signals_analysis_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Generate fixes JSON
    print("\nGenerating fixes JSON...")
    fixes = generate_fixes_json(dict(categories), all_signals)
    
    fixes_path = Path(__file__).parent.parent / "enum_signals_proposed_fixes.json"
    with open(fixes_path, 'w', encoding='utf-8') as f:
        json.dump(fixes, f, indent=2)
    print(f"Fixes JSON saved to: {fixes_path}")
    
    # Print summary to console
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nTotal enum signals: {len(enum_signals)}")
    print(f"\nBreakdown:")
    for cat_name, signals in sorted(categories.items()):
        print(f"  {cat_name}: {len(signals)}")
    
    print(f"\nFixes breakdown:")
    print(f"  High confidence fixes: {len(fixes['high_confidence_fixes'])}")
    print(f"  Medium confidence fixes: {len(fixes['medium_confidence_fixes'])}")
    print(f"  Needs manual review: {len(fixes['needs_manual_review'])}")
    print(f"  Merge metadata signals: {len(fixes['merge_metadata_signals'])}")
    
    print(f"\nFull report: {report_path}")
    print(f"Proposed fixes: {fixes_path}")

if __name__ == "__main__":
    main()
