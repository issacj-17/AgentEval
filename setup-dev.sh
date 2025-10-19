#!/bin/bash

# Development environment setup script for AgentEval
# This script sets up the development environment including pre-commit hooks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}   AgentEval Development Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}→${NC} Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if ! python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}✗ Python 3.11+ required. Current version: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python version: $PYTHON_VERSION"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠ Warning: No virtual environment detected${NC}"
    echo -e "${YELLOW}  Consider creating one with: python -m venv .venv${NC}"
    echo -e "${YELLOW}  Then activate it with: source .venv/bin/activate${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Virtual environment: $VIRTUAL_ENV"
fi

# Install development dependencies
echo ""
echo -e "${YELLOW}→${NC} Installing development dependencies..."
pip install -e ".[dev]" > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Development dependencies installed"

# Install pre-commit hooks
echo ""
echo -e "${YELLOW}→${NC} Installing pre-commit hooks..."
pre-commit install > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Pre-commit hooks installed"

# Set up custom git hooks
echo ""
echo -e "${YELLOW}→${NC} Setting up custom git hooks..."
if [ ! -d .git/hooks ]; then
    mkdir -p .git/hooks
fi

# Link custom pre-commit hook
if [ -f .githooks/pre-commit ]; then
    cp .githooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo -e "${GREEN}✓${NC} Custom git hooks configured"
else
    echo -e "${YELLOW}⚠ Custom pre-commit hook not found, skipping${NC}"
fi

# Run initial pre-commit on all files (optional)
echo ""
read -p "Run pre-commit checks on all files now? (recommended) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}→${NC} Running pre-commit on all files (this may take a moment)..."
    pre-commit run --all-files || echo -e "${YELLOW}⚠ Some checks failed. Run 'make format' to auto-fix formatting issues.${NC}"
fi

# Setup complete
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Development environment setup complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
echo -e "Quick reference:"
echo -e "  ${BLUE}make help${NC}            - Show all available commands"
echo -e "  ${BLUE}make format${NC}          - Format code with black and isort"
echo -e "  ${BLUE}make lint${NC}            - Run linting checks"
echo -e "  ${BLUE}make test${NC}            - Run tests with coverage"
echo -e "  ${BLUE}make test-all${NC}        - Run all checks and tests"
echo ""
echo -e "Pre-commit hooks will now run automatically on each commit."
echo -e "To skip hooks temporarily: ${YELLOW}git commit --no-verify${NC}"
echo ""
