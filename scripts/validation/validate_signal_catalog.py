#!/usr/bin/env python3
"""
Validate signals_catalog.json for runtime and data quality issues.

Checks performed:
- Catalog structure validation (via SignalsCatalog loader)
- Unknown derive operators (unsupported by SignalDerivation)
- Event references backed by known EDMC events
- Redundant enum entries (duplicate enum value ids)
- Potentially redundant event mappings (warnings)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CATALOG = PROJECT_ROOT / "data" / "signals_catalog.json"
DEFAULT_EVENTS_MD = PROJECT_ROOT / "docs" / "EDMC_EVENTS_CATALOG.md"

SUPPORTED_OPS: Set[str] = {
    "flag",
    "path",
    "map",
    "first_match",
    "event",
    "recent",
    "and",
    "or",
    "count",
    "exists",
    "sum",
    "any",
    "not",
    "eq",
    "ne",
    "lt",
    "lte",
    "gt",
    "gte",
    "match",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Path to signals_catalog.json (default: %(default)s)",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "md", "pdf", "both"),
        default="auto",
        help="Event authority source (default: %(default)s)",
    )
    parser.add_argument(
        "--events-md",
        type=Path,
        default=DEFAULT_EVENTS_MD,
        help="Path to EDMC event catalog markdown (used by md/both)",
    )
    parser.add_argument(
        "--events-pdf",
        type=Path,
        default=None,
        help="Path to Journal_Manual-v32.pdf (required for pdf/both)",
    )
    parser.add_argument(
        "--allow-synthetic",
        nargs="*",
        default=["StartUp", "ShutDown"],
        help="Extra non-journal events allowed in catalog",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings as failures (exit code 1)",
    )
    return parser.parse_args()


def flatten_signals(node: Dict[str, Any], prefix: str = "") -> Dict[str, Dict[str, Any]]:
    flat: Dict[str, Dict[str, Any]] = {}
    for key, value in node.items():
        if key.startswith("_"):
            continue
        full_name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and "type" in value:
            flat[full_name] = value
        elif isinstance(value, dict):
            flat.update(flatten_signals(value, full_name))
    return flat


def collect_event_refs(signal_name: str, obj: Any, path: str = "") -> List[Tuple[str, str, str]]:
    refs: List[Tuple[str, str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else key
            if key in {"event_name", "recent_event"} and isinstance(value, str):
                refs.append((signal_name, child_path, value))
            elif (
                key == "events"
                and isinstance(value, list)
                and path.endswith("sources.journal")
            ):
                for index, event_name in enumerate(value):
                    if isinstance(event_name, str):
                        refs.append((signal_name, f"{child_path}[{index}]", event_name))
            refs.extend(collect_event_refs(signal_name, value, child_path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            refs.extend(collect_event_refs(signal_name, value, f"{path}[{index}]"))
    return refs


def collect_ops(obj: Any, output: Set[str]) -> None:
    if isinstance(obj, dict):
        op = obj.get("op")
        if isinstance(op, str):
            output.add(op)
        for value in obj.values():
            collect_ops(value, output)
    elif isinstance(obj, list):
        for value in obj:
            collect_ops(value, output)


def extract_events_from_markdown(md_path: Path) -> Set[str]:
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown events file not found: {md_path}")
    text = md_path.read_text(encoding="utf-8")
    # Event entries in the catalog markdown are written as: ### `EventName`
    return set(re.findall(r"^###\s+`([^`]+)`\s*$", text, flags=re.MULTILINE))


def _find_ghostscript_binary() -> str:
    candidates = [
        shutil.which("gswin64c"),
        shutil.which("gs"),
        r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise RuntimeError("Ghostscript not found (needed for PDF event extraction)")


def extract_events_from_pdf(pdf_path: Path) -> Set[str]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF events file not found: {pdf_path}")

    gs_binary = _find_ghostscript_binary()
    text = subprocess.check_output(
        [
            gs_binary,
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=txtwrite",
            "-sOutputFile=-",
            str(pdf_path),
        ],
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    events: Set[str] = set()

    # Primary source: section index entries, e.g. "8.46 Shipyard"
    section_pattern = re.compile(r"^\s*(\d+)\.(\d+)\s+([A-Za-z][A-Za-z0-9]+)\s*$")
    for line in text.splitlines():
        match = section_pattern.match(line)
        if not match:
            continue
        major = int(match.group(1))
        event_name = match.group(3)
        if 3 <= major <= 13:
            events.add(event_name)

    # Secondary source: JSON examples in manual.
    sample_pattern = re.compile(r'["“]event["”]\s*:\s*["“]([A-Za-z0-9_]+)["”]')
    for event_name in sample_pattern.findall(text):
        if event_name.lower() == "eventname":
            continue
        if event_name.lower() == "fileheader":
            events.add("FileHeader")
        else:
            events.add(event_name)

    return events


def _auto_pdf_candidates() -> List[Path]:
    return [
        PROJECT_ROOT / "docs" / "Journal_Manual-v32.pdf",
        Path.home() / "Downloads" / "Journal_Manual-v32.pdf",
        Path.home() / "Downloads" / "Journal_Manual-v33.pdf",
    ]


def get_authoritative_events(
    source: str,
    events_md: Path,
    events_pdf: Path | None,
    synthetic: Iterable[str],
) -> Tuple[Set[str], str, Path | None]:
    valid_events: Set[str] = set()
    resolved_source = source
    resolved_pdf = events_pdf

    if source == "auto":
        if events_pdf is not None and events_pdf.exists():
            resolved_source = "pdf"
            resolved_pdf = events_pdf
        else:
            auto_pdf = next((p for p in _auto_pdf_candidates() if p.exists()), None)
            if auto_pdf is not None:
                resolved_source = "pdf"
                resolved_pdf = auto_pdf
            else:
                resolved_source = "md"

    if resolved_source in {"md", "both"}:
        valid_events.update(extract_events_from_markdown(events_md))

    if resolved_source in {"pdf", "both"}:
        if resolved_pdf is None:
            raise ValueError("--events-pdf is required when --source is pdf or both")
        valid_events.update(extract_events_from_pdf(resolved_pdf))

    valid_events.update(synthetic)
    return valid_events, resolved_source, resolved_pdf


def validate_catalog_structure(catalog_path: Path) -> List[str]:
    sys.path.insert(0, str(PROJECT_ROOT))
    errors: List[str] = []
    try:
        from src.edmcruleengine.signals_catalog import SignalsCatalog  # type: ignore

        SignalsCatalog.from_file(catalog_path)
    except Exception as exc:
        errors.append(f"Catalog structure validation failed: {type(exc).__name__}: {exc}")
    return errors


def main() -> int:
    args = parse_args()

    errors: List[str] = []
    warnings: List[str] = []

    if not args.catalog.exists():
        print(f"ERROR: Catalog file not found: {args.catalog}")
        return 2

    structure_errors = validate_catalog_structure(args.catalog)
    errors.extend(structure_errors)

    try:
        valid_events, resolved_source, resolved_pdf = get_authoritative_events(
            source=args.source,
            events_md=args.events_md,
            events_pdf=args.events_pdf,
            synthetic=args.allow_synthetic,
        )
    except Exception as exc:
        print(f"ERROR: Failed to load authoritative events: {type(exc).__name__}: {exc}")
        return 2

    catalog_data = json.loads(args.catalog.read_text(encoding="utf-8"))
    flat_signals = flatten_signals(catalog_data.get("signals", {}))

    event_refs: List[Tuple[str, str, str]] = []
    used_ops: Set[str] = set()

    for signal_name, signal_def in flat_signals.items():
        event_refs.extend(collect_event_refs(signal_name, signal_def))
        collect_ops(signal_def, used_ops)

        if signal_def.get("type") == "enum":
            values = signal_def.get("values", [])
            if isinstance(values, list):
                enum_id_counts = Counter()
                recent_event_counts = Counter()
                value_signature_counts = Counter()

                for value_def in values:
                    if not isinstance(value_def, dict):
                        continue

                    value_id = value_def.get("value")
                    if value_id is not None:
                        enum_id_counts[value_id] += 1

                    recent_event = value_def.get("recent_event")
                    if isinstance(recent_event, str):
                        recent_event_counts[recent_event] += 1

                    signature = (
                        value_def.get("value"),
                        value_def.get("label"),
                        value_def.get("recent_event"),
                    )
                    value_signature_counts[signature] += 1

                duplicate_value_ids = sorted(
                    value_id for value_id, count in enum_id_counts.items() if count > 1
                )
                for value_id in duplicate_value_ids:
                    errors.append(
                        f"[{signal_name}] duplicate enum value id: {value_id!r}"
                    )

                duplicate_signatures = sorted(
                    signature
                    for signature, count in value_signature_counts.items()
                    if count > 1
                )
                for signature in duplicate_signatures:
                    warnings.append(
                        f"[{signal_name}] duplicate enum entry tuple: {signature!r}"
                    )

                duplicate_recent_events = sorted(
                    event_name
                    for event_name, count in recent_event_counts.items()
                    if count > 1
                )
                for event_name in duplicate_recent_events:
                    warnings.append(
                        f"[{signal_name}] repeated recent_event mapping: {event_name}"
                    )

    unknown_ops = sorted(op for op in used_ops if op not in SUPPORTED_OPS)
    for op in unknown_ops:
        errors.append(f"Unknown derive op in catalog: {op!r}")

    invalid_refs: List[Tuple[str, str, str]] = [
        (signal_name, location, event_name)
        for signal_name, location, event_name in event_refs
        if event_name not in valid_events
    ]
    for signal_name, location, event_name in invalid_refs:
        errors.append(
            f"[{signal_name}] invalid event reference at {location}: {event_name!r}"
        )

    distinct_refs = {event_name for _, _, event_name in event_refs}
    print("Signal Catalog Validation")
    print("=" * 40)
    print(f"Catalog: {args.catalog}")
    print(f"Authority source: {resolved_source} (requested: {args.source})")
    if resolved_source in {"md", "both"}:
        print(f"Events markdown: {args.events_md}")
    if resolved_source in {"pdf", "both"}:
        print(f"Events PDF: {resolved_pdf}")
    print(f"Signals checked: {len(flat_signals)}")
    print(f"Distinct event refs: {len(distinct_refs)}")
    print(f"Authoritative events: {len(valid_events)}")
    print(f"Unknown ops: {len(unknown_ops)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Errors: {len(errors)}")

    if warnings:
        print("\nWarnings")
        print("-" * 40)
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nErrors")
        print("-" * 40)
        for error in errors:
            print(f"- {error}")
        return 1

    if args.strict_warnings and warnings:
        print("\nValidation failed due to --strict-warnings.")
        return 1

    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
