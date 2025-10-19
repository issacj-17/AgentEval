#!/usr/bin/env bash
# Backward compatibility wrapper that delegates to the Python orchestrator.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_ROOT}/src" python3 -m agenteval.cli.live_demo "$@"
