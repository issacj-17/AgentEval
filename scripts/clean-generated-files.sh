#!/usr/bin/env bash
#
# clean-generated-files.sh
# ========================
# Cleans all generated files and directories from AgentEval runs.
#
# This includes:
# - Auto-pulled campaign results
# - HTML dashboards and reports
# - Markdown evidence reports
# - Python cache files
# - Test coverage files
# - Demo logs
#
# Usage:
#   ./scripts/clean-generated-files.sh [--force]
#
# Options:
#   --force    Skip confirmation prompt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

echo "================================================"
echo "  AgentEval - Clean Generated Files"
echo "================================================"
echo ""

# List of directories/files to clean
ITEMS_TO_CLEAN=(
    "outputs"
    "demo/evidence/reports"
    "demo/evidence/dashboard.md"
    "demo/evidence/live-demo-latest.md"
    "demo/evidence/pulled-results"
    "demo/*.log"
    "htmlcov"
    ".coverage"
    ".pytest_cache"
)

echo "The following will be removed:"
echo ""
for item in "${ITEMS_TO_CLEAN[@]}"; do
    if [[ -e "${REPO_ROOT}/${item}" ]] || ls ${REPO_ROOT}/${item} 2>/dev/null | grep -q .; then
        echo "  - ${item}"
    fi
done
echo ""
echo "Python cache files (__pycache__, *.pyc) will also be removed."
echo ""

# Confirmation
if [[ "${FORCE}" != "true" ]]; then
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}ℹ${NC} Cleaning generated files..."

# Change to repo root
cd "${REPO_ROOT}"

# Remove directories
for dir in "outputs" "demo/evidence/reports" "demo/evidence/pulled-results" "htmlcov" ".pytest_cache"; do
    if [[ -d "${dir}" ]]; then
        echo -e "${BLUE}ℹ${NC} Removing directory: ${dir}"
        rm -rf "${dir}"
    fi
done

# Remove specific files
for file in "demo/evidence/dashboard.md" "demo/evidence/live-demo-latest.md" ".coverage"; do
    if [[ -f "${file}" ]]; then
        echo -e "${BLUE}ℹ${NC} Removing file: ${file}"
        rm -f "${file}"
    fi
done

# Remove demo logs
if ls demo/*.log 1> /dev/null 2>&1; then
    echo -e "${BLUE}ℹ${NC} Removing demo logs"
    rm -f demo/*.log
fi

# Remove Python cache
echo -e "${BLUE}ℹ${NC} Removing Python cache files"
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo ""
echo -e "${GREEN}✓${NC} Cleanup complete!"
echo ""

# Verify cleanup
echo "Verification:"
CLEAN=true

if [[ -d "outputs" ]]; then
    echo -e "${RED}✗${NC} outputs/ still exists"
    CLEAN=false
else
    echo -e "${GREEN}✓${NC} outputs/ removed"
fi

if [[ -d "demo/evidence/reports" ]]; then
    echo -e "${RED}✗${NC} demo/evidence/reports/ still exists"
    CLEAN=false
else
    echo -e "${GREEN}✓${NC} demo/evidence/reports/ removed"
fi

if [[ -f "demo/evidence/dashboard.md" ]]; then
    echo -e "${RED}✗${NC} demo/evidence/dashboard.md still exists"
    CLEAN=false
else
    echo -e "${GREEN}✓${NC} demo/evidence/dashboard.md removed"
fi

echo ""

if [[ "${CLEAN}" == "true" ]]; then
    echo -e "${GREEN}✓${NC} Repository is clean and ready for fresh demo!"
else
    echo -e "${YELLOW}⚠${NC} Some files could not be removed. Check permissions."
fi

echo ""
echo "================================================"
