Acceptance Checklist

- Tool is registered; agents can call it.
  - `app/my_tools.py` contains `TOOL_CLASSES['CodexMCPTool'] = MyCodexMCPTool` when `CODEX_MCP_URL` is non-empty.
  - `app/pg_tools.py` lists `CodexMCPTool` in available tools via `TOOL_CLASSES`.
  - `app/my_agent.py` shows `CodexMCPTool` in the tool multiselect and `create_tool()` returns an instance of `CodexMCPTool`.

- propose_change returns plan_id + preview_diff via Studio action.
  - From a running app, select `CodexMCPTool` and run with `action="propose_change"`, `repo_root` set to project root, `include=["spec/**/*.md"]`, `objective="Plan-only Codex wiring"`.
  - Verify the tool returns a dict with non-empty `plan_id` and `preview_diff` fields.

- apply_change (local) returns branch, changed_files, commit_sha.
  - Using a valid `plan_id`, run `action="apply_change"`, `strategy="local"`, `branch="feature/codex-mcp-apply"`, `commit_message="chore(codex): apply planned changes"`.
  - Verify result includes `branch="feature/codex-mcp-apply"`, `changed_files` (>=1), `commit_sha` (40 hex chars).

- Errors from MCP are surfaced with clear messages (exercise at least PATH_DENIED and DIFF_LIMIT_EXCEEDED).
  - Mock server responses (unit) return JSON-RPC error objects with `code` mapping to `PATH_DENIED` and `DIFF_LIMIT_EXCEEDED`.
  - Verify surfaced Studio errors contain `403_PATH_DENIED` and `413_DIFF_LIMIT_EXCEEDED` and include concrete file/diff size messages.

- Env-driven config works (CODEX_MCP_URL, CODEX_TIMEOUT_SEC); documented in README.md.
  - Set `CODEX_MCP_URL` to `http://localhost:8765/` and `CODEX_TIMEOUT_SEC=30`; restart app; the tool uses new values.
  - README.md updated with a section "Codex MCP Tool" listing both env vars, defaults, and purpose.

- Unit tests (mock MCP) pass locally and in CI.
  - Run: `pytest -q tests/test_codex_mcp_tool.py` locally → all tests green.
  - CI job runs same and reports success.

- Smoke test steps documented and reproducible.
  - Ensure Codex MCP server is running at `http://localhost:8765/`.
  - Run: `bash scripts/smoke_codex_mcp.sh`.
  - Verify script prints or logs a non-empty `plan_id` and `preview_diff` for `propose_change` and exits 0.

Out of Scope

- UI polish beyond existing selection/execution.
- Review/explain dedicated UI components.
- PR-mode auto-auth and remote PR creation flows (v2).

Roll-back Plan

- Set `CODEX_MCP_URL` to an empty string in `.env` and restart. Because `app/my_tools.py` registers `CodexMCPTool` only if `CODEX_MCP_URL` is non-empty, the tool will not register and will disappear from the UI.
- As an immediate fallback, remove or comment the `TOOL_CLASSES['CodexMCPTool'] = MyCodexMCPTool` line in `app/my_tools.py` and restart the app.
