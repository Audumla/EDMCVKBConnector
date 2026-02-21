#!/bin/bash
# release.sh - One-command release workflow
#
# This script prepares the changelog and triggers the release-please workflow
# in a single step. Suitable for running from VSCode tasks or CI/CD.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[Release Workflow]${NC} Starting release workflow..."
echo ""

# Step 1: Prepare changelog
echo -e "${YELLOW}[Step 1/2]${NC} Preparing changelog..."
python scripts/changelog_activity.py --strict || {
    echo -e "${RED}✗ Changelog preparation failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Changelog prepared${NC}"
echo ""

# Step 2: Trigger release-please workflow
echo -e "${YELLOW}[Step 2/2]${NC} Triggering release-please workflow..."
gh workflow run release-please.yml || {
    echo -e "${RED}✗ Failed to trigger workflow (ensure 'gh' CLI is installed and authenticated)${NC}"
    exit 1
}
echo -e "${GREEN}✓ Release workflow triggered${NC}"
echo ""

echo -e "${GREEN}[Release Workflow]${NC} Complete! Check GitHub for the release PR."
echo ""
echo "Release notes preview: dist/RELEASE_NOTES.preview.md"
echo "Next: Review the release PR on GitHub, merge to finalize release."
