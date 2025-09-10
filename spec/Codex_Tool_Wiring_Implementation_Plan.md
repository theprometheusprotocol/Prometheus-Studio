Overview

Wire Codex as a Studio tool backed by an MCP JSON-RPC client that talks to a running Codex MCP server at `http://localhost:8765/`. The scope covers adding a new tool module, registering it in the existing tools registry so agents can select and call it, environment-based configuration, request/response mapping to JSON-RPC methods, error surfacing, and unit + smoke tests, without UI polish beyond existing selection and execution flows.

File Changes (exact paths)

- Tool module: `app/tools/CodexMCPTool.py`
- Registry wiring: `app/my_tools.py` (add `MyCodexMCPTool` and register `'CodexMCPTool'` in `TOOL_CLASSES`)
- Config/env updates: `.env.example` (append `CODEX_MCP_URL`, `CODEX_TIMEOUT_SEC`), tool reads via `os.getenv` in `app/tools/CodexMCPTool.py`
- Optional UI hooks: `app/pg_tools.py` (existing tool runner panel; no code changes required), `app/my_agent.py` (existing tool selection; no code changes required)
- Tests: `tests/test_codex_mcp_tool.py` (unit, mock MCP), `tests/fixtures/codex_mcp/*.json` (JSON-RPC fixtures), `scripts/smoke_codex_mcp.sh` + `tests/smoke_codex_mcp.py` (smoke)

Method Signatures

In `app/tools/CodexMCPTool.py`:

- `class CodexMCPClient:`
  - `def __init__(self, base_url: str, timeout_sec: int) -> None:`
  - `def propose_change(self, repo_root: str, include: list[str], exclude: list[str], objective: str, context: list[dict], dry_run: bool = True) -> dict:`
  - `def apply_change(self, plan_id: str, strategy: str, branch: str, commit_message: str) -> dict:`
  - `def review_code(self, paths: list[str], rules: list[str]) -> dict:`
  - `def explain_change(self, plan_id: str) -> dict:`

- `from crewai.tools import BaseTool`
- `class CodexMCPTool(BaseTool):`
  - `name: str = "CodexMCPTool"`
  - `description: str = "Plan, apply, review and explain code changes via Codex MCP."`
  - `args_schema = CodexMCPToolInputSchema`
  - `def __init__(self, base_url: str | None = None, timeout_sec: int | None = None) -> None:`
  - `def run(self, inputs: CodexMCPToolInputSchema) -> dict:`
  - Dispatches to one of: `propose_change(...)`, `apply_change(...)`, `review_code(...)`, `explain_change(...)` on an internal `CodexMCPClient` instance based on `inputs.action`.

- `class CodexMCPToolInputSchema(BaseModel):`
  - `action: Literal["propose_change","apply_change","review_code","explain_change"]`
  - plus method-specific fields (see Request/Response Payloads → Params Mapping).

- `class MyCodexMCPTool(MyTool):` in `app/my_tools.py`
  - `def __init__(self, tool_id=None, base_url=None, timeout_sec=None):`
  - `def create_tool(self) -> CodexMCPTool:`

Request/Response Payloads

JSON-RPC 2.0, single endpoint `POST {CODEX_MCP_URL}` with `Content-Type: application/json`.

1) propose_change

- Request
  - Method: `codex.propose_change`
  - Body:
    {
      "jsonrpc": "2.0",
      "id": "<uuid>",
      "method": "codex.propose_change",
      "params": {
        "repo_root": "<absolute-or-cwd-root>",
        "include": ["app/**/*.py", "spec/**/*.md"],
        "exclude": ["**/__pycache__/**", "**/.git/**"],
        "objective": "<natural language objective>",
        "context": [{"path": "README.md"}],
        "dry_run": true
      }
    }

- Result
  - HTTP 200 with:
    {
      "jsonrpc": "2.0",
      "id": "<same-as-request-id>",
      "result": {
        "plan_id": "<uuid>",
        "preview_diff": "<unified-diff-string>",
        "summary": "<short summary>",
        "files": ["app/tools/CodexMCPTool.py", "app/my_tools.py"]
      }
    }

2) apply_change

- Request
  - Method: `codex.apply_change`
  - Body:
    {
      "jsonrpc": "2.0",
      "id": "<uuid>",
      "method": "codex.apply_change",
      "params": {
        "plan_id": "<uuid>",
        "strategy": "local",
        "branch": "feature/codex-mcp-apply",
        "commit_message": "chore(codex): apply planned changes"
      }
    }

- Result
  - HTTP 200 with:
    {
      "jsonrpc": "2.0",
      "id": "<same-as-request-id>",
      "result": {
        "branch": "feature/codex-mcp-apply",
        "changed_files": ["app/tools/CodexMCPTool.py"],
        "commit_sha": "<40-hex>",
        "summary": "<short summary>"
      }
    }

3) review_code

- Request
  - Method: `codex.review_code`
  - Body:
    {
      "jsonrpc": "2.0",
      "id": "<uuid>",
      "method": "codex.review_code",
      "params": {
        "paths": ["app/tools/CodexMCPTool.py"],
        "rules": ["no-secrets", "complexity<=10"]
      }
    }

- Result
  - HTTP 200 with:
    {
      "jsonrpc": "2.0",
      "id": "<same-as-request-id>",
      "result": {
        "findings": [
          {"path": "app/tools/CodexMCPTool.py", "line": 42, "level": "warning", "message": "Cyclomatic complexity 12", "ruleId": "complexity"}
        ]
      }
    }

4) explain_change

- Request
  - Method: `codex.explain_change`
  - Body:
    {
      "jsonrpc": "2.0",
      "id": "<uuid>",
      "method": "codex.explain_change",
      "params": {
        "plan_id": "<uuid>"
      }
    }

- Result
  - HTTP 200 with:
    {
      "jsonrpc": "2.0",
      "id": "<same-as-request-id>",
      "result": {
        "explanation_markdown": "## What changed...\n..."
      }
    }

Params Mapping to Input Schema and Returns

- Input schema fields for `CodexMCPToolInputSchema`:
  - `action` → one of the four actions above.
  - For `propose_change`: `repo_root: str`, `include: list[str]`, `exclude: list[str]`, `objective: str`, `context: list[dict]`, `dry_run: bool=True`.
  - For `apply_change`: `plan_id: str`, `strategy: Literal["local"]`, `branch: str`, `commit_message: str`.
  - For `review_code`: `paths: list[str]`, `rules: list[str]`.
  - For `explain_change`: `plan_id: str`.

- Return objects (tool `run` returns these dicts directly):
  - `propose_change` → `{ "plan_id": str, "preview_diff": str, "summary": str, "files": list[str] }`
  - `apply_change` → `{ "branch": str, "changed_files": list[str], "commit_sha": str, "summary": str }`
  - `review_code` → `{ "findings": list[dict] }`
  - `explain_change` → `{ "explanation_markdown": str }`

Error Handling

Map MCP errors to Studio-surfaced errors with consistent messages and codes.

- INVALID_INPUT → Studio code `400_INVALID_INPUT`
  - Example: "Invalid input: objective must be non-empty."
- PATH_DENIED → Studio code `403_PATH_DENIED`
  - Example: "Path denied: app/secret_config.py is outside allowed scope."
- DIFF_LIMIT_EXCEEDED → Studio code `413_DIFF_LIMIT_EXCEEDED`
  - Example: "Diff limit exceeded: proposed patch is too large (limit 5000 lines)."
- TIMEOUT → Studio code `504_TIMEOUT`
  - Example: "Codex MCP timed out after 60s while proposing changes."
- GITHUB_AUTH_ERROR → Studio code `401_GITHUB_AUTH_ERROR`
  - Example: "GitHub authentication failed: token missing or invalid."
- PR_CREATION_FAILED → Studio code `502_PR_CREATION_FAILED`
  - Example: "Failed to create pull request: upstream service error."
- CODEX_EXECUTION_ERROR → Studio code `500_CODEX_EXECUTION_ERROR`
  - Example: "Codex execution error: unexpected tool failure; see server logs."

Environment Variables

- `CODEX_MCP_URL`
  - Default: `http://localhost:8765/`
  - Read in: `app/tools/CodexMCPTool.py` during `CodexMCPTool.__init__`
- `CODEX_TIMEOUT_SEC`
  - Default: `60`
  - Read in: `app/tools/CodexMCPTool.py` during `CodexMCPTool.__init__`

Exact `.env.example` additions (append at end of file):

CODEX_MCP_URL=http://localhost:8765/
CODEX_TIMEOUT_SEC=60

Code Snippets (planned)

1) Read env and construct client

from pydantic import BaseModel
import os, requests, uuid

class CodexMCPClient:
    def __init__(self, base_url: str, timeout_sec: int) -> None:
        self.base_url = base_url
        self.timeout = timeout_sec

    def _rpc(self, method: str, params: dict) -> dict:
        body = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
        resp = requests.post(self.base_url, json=body, timeout=self.timeout)
        payload = resp.json()
        if "error" in payload:
            raise RuntimeError(payload["error"]["message"])  # mapped by caller
        return payload["result"]

2) Tool init and dispatch

class CodexMCPTool(BaseTool):
    name: str = "CodexMCPTool"
    description: str = "Plan, apply, review and explain code changes via Codex MCP."
    args_schema = CodexMCPToolInputSchema

    def __init__(self, base_url: str | None = None, timeout_sec: int | None = None) -> None:
        base_url = base_url or os.getenv("CODEX_MCP_URL", "http://localhost:8765/")
        timeout = int(timeout_sec or os.getenv("CODEX_TIMEOUT_SEC", "60"))
        self.client = CodexMCPClient(base_url, timeout)

    def run(self, inputs: CodexMCPToolInputSchema) -> dict:
        if inputs.action == "propose_change":
            return self.client.propose_change(inputs.repo_root, inputs.include, inputs.exclude, inputs.objective, inputs.context, inputs.dry_run)
        if inputs.action == "apply_change":
            return self.client.apply_change(inputs.plan_id, inputs.strategy, inputs.branch, inputs.commit_message)
        if inputs.action == "review_code":
            return self.client.review_code(inputs.paths, inputs.rules)
        if inputs.action == "explain_change":
            return self.client.explain_change(inputs.plan_id)
        raise ValueError(f"Unknown action: {inputs.action}")

3) Registry wiring (conditional registration for rollback via config)

# app/my_tools.py
from tools.CodexMCPTool import CodexMCPTool

class MyCodexMCPTool(MyTool):
    def __init__(self, tool_id=None, base_url=None, timeout_sec=None):
        parameters = {
            'base_url': {'mandatory': False},
            'timeout_sec': {'mandatory': False}
        }
        super().__init__(tool_id, 'CodexMCPTool', "Plan, apply, review and explain code changes via Codex MCP.", parameters, base_url=base_url, timeout_sec=timeout_sec)

    def create_tool(self) -> CodexMCPTool:
        return CodexMCPTool(
            base_url=self.parameters.get('base_url') if self.parameters.get('base_url') else None,
            timeout_sec=int(self.parameters.get('timeout_sec')) if self.parameters.get('timeout_sec') else None
        )

# At the bottom, near TOOL_CLASSES
import os as _os
if _os.getenv('CODEX_MCP_URL', 'http://localhost:8765/').strip():
    TOOL_CLASSES['CodexMCPTool'] = MyCodexMCPTool

Test Plan

- Unit (mock MCP):
  - Files: `tests/test_codex_mcp_tool.py`, `tests/fixtures/codex_mcp/propose_ok.json`, `tests/fixtures/codex_mcp/apply_ok.json`, `tests/fixtures/codex_mcp/review_ok.json`, `tests/fixtures/codex_mcp/explain_ok.json`, `tests/fixtures/codex_mcp/path_denied.json`, `tests/fixtures/codex_mcp/diff_limit_exceeded.json`.
  - Mocks: Use `responses` to stub `POST {CODEX_MCP_URL}` and return the JSON fixtures for each method.
  - Commands:
    - `pytest -q tests/test_codex_mcp_tool.py`
    - CI: rely on existing workflow; no additions required.

- Smoke (real server at http://localhost:8765/):
  - Files: `scripts/smoke_codex_mcp.sh`, `tests/smoke_codex_mcp.py`.
  - `scripts/smoke_codex_mcp.sh`:
    #!/usr/bin/env bash
    set -euo pipefail
    export CODEX_MCP_URL=${CODEX_MCP_URL:-http://localhost:8765/}
    export CODEX_TIMEOUT_SEC=${CODEX_TIMEOUT_SEC:-60}
    python tests/smoke_codex_mcp.py
  - `tests/smoke_codex_mcp.py` performs `propose_change` on this repo with `include=["spec/**/*.md"]`, asserts `plan_id` and `preview_diff` present, then exits without applying.
  - Commands:
    - `bash scripts/smoke_codex_mcp.sh`

Exact Params for Unit Calls

- propose_change call in unit test:
  - `client.propose_change(repo_root=os.getcwd(), include=["app/**/*.py"], exclude=["**/__pycache__/**"], objective="Add Codex MCP tool", context=[], dry_run=True)`
- apply_change call in unit test:
  - `client.apply_change(plan_id="00000000-0000-0000-0000-000000000000", strategy="local", branch="feature/codex-apply-test", commit_message="test: apply change via codex")`
- review_code call in unit test:
  - `client.review_code(paths=["app/tools/CodexMCPTool.py"], rules=["no-secrets"])`
- explain_change call in unit test:
  - `client.explain_change(plan_id="00000000-0000-0000-0000-000000000000")`

Estimated Diff Size

- Files touched: 7
  - `app/tools/CodexMCPTool.py` (~200 LOC)
  - `app/my_tools.py` (+30 LOC)
  - `.env.example` (+2 LOC)
  - `tests/test_codex_mcp_tool.py` (~220 LOC)
  - `tests/fixtures/codex_mcp/*.json` (6 files, ~120 LOC total)
  - `scripts/smoke_codex_mcp.sh` (10 LOC)
  - `tests/smoke_codex_mcp.py` (~60 LOC)

- Risk notes
  - Network failures/timeouts: handled via `CODEX_TIMEOUT_SEC` and error mapping to `504_TIMEOUT` with actionable messages.
  - Large diffs: surfaced as `413_DIFF_LIMIT_EXCEEDED` with clear guidance.
  - Path restrictions: surfaced as `403_PATH_DENIED` and do not proceed to apply.
  - Server contract drift: JSON-RPC methods fixed per this plan; tests will fail fast if manifest diverges.
