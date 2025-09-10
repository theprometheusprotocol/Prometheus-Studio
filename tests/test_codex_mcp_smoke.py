# tests/test_codex_mcp_smoke.py
import os
import sys
from pathlib import Path

# Ensure repo root (where 'app/' lives) is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.tools.CodexMCPTool import CodexMCPClient  # noqa: E402

def test_smoke_propose_change():
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")
    timeout = int(os.getenv("CODEX_TIMEOUT_SEC", "60"))

    client = CodexMCPClient(base_url=url, timeout_sec=timeout)

    result = client.propose_change(
        goal="Plan-only Codex wiring",
        context="",
        repoRef={"mode": "local", "repo_path": str(ROOT)},
        constraints={"max_files": 10, "max_loc": 200, "timeout_sec": timeout},
        dry_run=True,
    )

    assert result.get("plan_id"), "Expected non-empty plan_id"
    assert result.get("preview_diff"), "Expected non-empty preview_diff"
