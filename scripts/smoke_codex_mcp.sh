#!/usr/bin/env bash
set -euo pipefail

export CODEX_MCP_URL=${CODEX_MCP_URL:-http://localhost:8765/}
export CODEX_TIMEOUT_SEC=${CODEX_TIMEOUT_SEC:-60}

python tests/smoke_codex_mcp.py

