# tests/test_codex_mcp_smoke.py
import os
import sys
import json
from pathlib import Path

# Ensure repo root (where 'app/' lives) is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.tools.CodexMCPTool import CodexMCPClient  # noqa: E402
import responses  # noqa: E402


def _fixture():
    path = ROOT / "tests" / "fixtures" / "codex_mcp" / "propose_ok.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@responses.activate
def test_smoke_propose_change():
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")
    timeout = int(os.getenv("CODEX_TIMEOUT_SEC", "60"))

    def dispatch(request):
        payload = json.loads(request.body.decode())
        if payload.get("method") == "propose_change":
            body = _fixture()
            return (200, {"Content-Type": "application/json"}, json.dumps(body))
        return (500, {}, json.dumps({"jsonrpc": "2.0", "id": "x", "error": {"code": "CODEX_EXECUTION_ERROR", "message": "unexpected"}}))

    responses.add_callback(responses.POST, url.rstrip("/") + "/", callback=dispatch, content_type="application/json")

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
