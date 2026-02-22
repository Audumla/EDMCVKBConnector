#!/bin/bash
# release.sh - Wrapper around scripts/release_workflow.py

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

python scripts/release/release_workflow.py "$@"
