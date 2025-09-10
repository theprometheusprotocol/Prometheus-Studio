import json
import os
from pathlib import Path

import pytest
import responses
import requests

from app.tools.CodexMCPTool import CodexMCPClient, CodexMCPTool, CodexMCPError, CodexMCPToolInputSchema


FIXTURES = Path(__file__).parent / "fixtures" / "codex_mcp"


def _load(name: str) -> dict:
    with open(FIXTURES / name, "r", encoding="utf-8") as f:
        return json.load(f)


@responses.activate
def test_client_propose_change_ok(monkeypatch):
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")

    def dispatch(request):
        payload = json.loads(request.body.decode())
        method = payload.get("method")
        if method == "propose_change":
            return (200, {"Content-Type": "application/json"}, json.dumps(_load("propose_ok.json")))
        return (500, {}, json.dumps({"jsonrpc": "2.0", "id": "x", "error": {"code": "CODEX_EXECUTION_ERROR", "message": "unexpected"}}))

    responses.add_callback(
        responses.POST,
        url,
        callback=dispatch,
        content_type="application/json",
    )

    client = CodexMCPClient(base_url=url, timeout_sec=30)
    result = client.propose_change(
        goal="Add Codex MCP tool",
        context="",
        repoRef={"mode": "local", "repo_path": os.getcwd()},
        constraints={"max_files": 10, "max_loc": 200, "timeout_sec": 60},
        dry_run=True,
    )
    assert "plan_id" in result and result["plan_id"]
    assert "preview_diff" in result and result["preview_diff"].startswith("--- ")


@responses.activate
def test_apply_change_ok():
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")

    def dispatch(request):
        payload = json.loads(request.body.decode())
        method = payload.get("method")
        if method == "apply_change":
            return (200, {"Content-Type": "application/json"}, json.dumps(_load("apply_ok.json")))
        return (500, {}, json.dumps({"jsonrpc": "2.0", "id": "x", "error": {"code": "CODEX_EXECUTION_ERROR", "message": "unexpected"}}))

    responses.add_callback(responses.POST, url, callback=dispatch, content_type="application/json")

    client = CodexMCPClient(base_url=url, timeout_sec=15)
    result = client.apply_change(
        plan_id="00000000-0000-0000-0000-000000000000",
        goal="test apply",
        repoRef={"mode": "local", "repo_path": os.getcwd()},
        constraints={"max_files": 10, "max_loc": 200, "timeout_sec": 60},
        run_checks=False,
        open_pr=False,
        branch_prefix="feature/codex-mcp-apply",
        dry_run=False,
    )
    assert result["branch"] == "feature/codex-mcp-apply"
    assert isinstance(result.get("changed_files"), list) and result.get("commit_sha")


@responses.activate
def test_path_denied_error_is_mapped():
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")

    def dispatch(request):
        payload = json.loads(request.body.decode())
        method = payload.get("method")
        if method == "propose_change":
            return (200, {"Content-Type": "application/json"}, json.dumps(_load("path_denied.json")))
        return (500, {}, json.dumps({"jsonrpc": "2.0", "id": "x", "error": {"code": "CODEX_EXECUTION_ERROR", "message": "unexpected"}}))

    responses.add_callback(responses.POST, url, callback=dispatch, content_type="application/json")

    client = CodexMCPClient(base_url=url, timeout_sec=5)
    with pytest.raises(CodexMCPError) as ei:
        client.propose_change(
            goal="",
            context="",
            repoRef={"mode": "local", "repo_path": os.getcwd()},
            constraints={"max_files": 10, "max_loc": 200, "timeout_sec": 60},
            dry_run=True,
        )
    assert "403_PATH_DENIED" in str(ei.value)


@responses.activate
def test_diff_limit_error_is_mapped():
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")

    def dispatch(request):
        payload = json.loads(request.body.decode())
        method = payload.get("method")
        if method == "propose_change":
            return (200, {"Content-Type": "application/json"}, json.dumps(_load("diff_limit_exceeded.json")))
        return (500, {}, json.dumps({"jsonrpc": "2.0", "id": "x", "error": {"code": "CODEX_EXECUTION_ERROR", "message": "unexpected"}}))

    responses.add_callback(responses.POST, url, callback=dispatch, content_type="application/json")

    client = CodexMCPClient(base_url=url, timeout_sec=10)
    with pytest.raises(CodexMCPError) as ei:
        client.propose_change(
            goal="Big change",
            context="",
            repoRef={"mode": "local", "repo_path": os.getcwd()},
            constraints={"max_files": 1, "max_loc": 1, "timeout_sec": 1},
            dry_run=True,
        )
    assert "413_DIFF_LIMIT_EXCEEDED" in str(ei.value)


@responses.activate
def test_timeout_is_mapped(monkeypatch):
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")

    def raise_timeout(request):
        raise requests.Timeout()

    import requests as _requests
    responses.add_callback(responses.POST, url, callback=lambda r: (_ for _ in ()).throw(_requests.Timeout()))

    client = CodexMCPClient(base_url=url, timeout_sec=1)
    with pytest.raises(CodexMCPError) as ei:
        client.explain_change(plan_id="00000000-0000-0000-0000-000000000000")
    assert "504_TIMEOUT" in str(ei.value)
