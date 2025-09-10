import os
import uuid
from typing import Literal, List, Dict, Any, Optional

import requests
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class CodexMCPError(RuntimeError):
    def __init__(self, studio_code: str, message: str):
        super().__init__(f"{studio_code}: {message}")
        self.studio_code = studio_code
        self.message = message


def _map_mcp_error(err: Dict[str, Any]) -> CodexMCPError:
    # Accept codes as either numeric or string identifiers; prefer string identifiers.
    code = err.get("code")
    msg = err.get("message", "Unknown Codex MCP error")

    # Normalize to string identifier if nested under data
    if isinstance(code, int):
        # Fallback numeric mapping (generic)
        numeric_map = {
            -32602: "400_INVALID_INPUT",
            -32000: "500_CODEX_EXECUTION_ERROR",
        }
        studio_code = numeric_map.get(code, "500_CODEX_EXECUTION_ERROR")
    else:
        # code may be a string like PATH_DENIED
        str_code = str(code or "CODEX_EXECUTION_ERROR").upper()
        mapping = {
            "INVALID_INPUT": "400_INVALID_INPUT",
            "PATH_DENIED": "403_PATH_DENIED",
            "DIFF_LIMIT_EXCEEDED": "413_DIFF_LIMIT_EXCEEDED",
            "TIMEOUT": "504_TIMEOUT",
            "GITHUB_AUTH_ERROR": "401_GITHUB_AUTH_ERROR",
            "PR_CREATION_FAILED": "502_PR_CREATION_FAILED",
            "CODEX_EXECUTION_ERROR": "500_CODEX_EXECUTION_ERROR",
        }
        studio_code = mapping.get(str_code, "500_CODEX_EXECUTION_ERROR")

    return CodexMCPError(studio_code, msg)


class CodexMCPClient:
    def __init__(self, base_url: str, timeout_sec: int) -> None:
        self.base_url = base_url
        self.timeout = timeout_sec

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
        try:
            resp = requests.post(self.base_url, json=body, timeout=self.timeout)
            resp.raise_for_status()
        except requests.Timeout as e:
            raise CodexMCPError("504_TIMEOUT", f"Codex MCP timed out after {self.timeout}s while calling {method}.") from e
        except requests.RequestException as e:
            raise CodexMCPError("500_CODEX_EXECUTION_ERROR", f"HTTP error contacting Codex MCP: {e}") from e

        try:
            payload = resp.json()
        except ValueError as e:
            raise CodexMCPError("500_CODEX_EXECUTION_ERROR", "Invalid JSON response from Codex MCP.") from e

        if "error" in payload and payload["error"]:
            raise _map_mcp_error(payload["error"])  # type: ignore[arg-type]

        return payload.get("result", {})

    def propose_change(
        self,
        repo_root: str,
        include: List[str],
        exclude: List[str],
        objective: str,
        context: List[Dict[str, Any]],
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        return self._rpc(
            "codex.propose_change",
            {
                "repo_root": repo_root,
                "include": include,
                "exclude": exclude,
                "objective": objective,
                "context": context,
                "dry_run": dry_run,
            },
        )

    def apply_change(
        self,
        plan_id: str,
        strategy: str,
        branch: str,
        commit_message: str,
    ) -> Dict[str, Any]:
        return self._rpc(
            "codex.apply_change",
            {
                "plan_id": plan_id,
                "strategy": strategy,
                "branch": branch,
                "commit_message": commit_message,
            },
        )

    def review_code(self, paths: List[str], rules: List[str]) -> Dict[str, Any]:
        return self._rpc(
            "codex.review_code",
            {
                "paths": paths,
                "rules": rules,
            },
        )

    def explain_change(self, plan_id: str) -> Dict[str, Any]:
        return self._rpc(
            "codex.explain_change",
            {
                "plan_id": plan_id,
            },
        )


class CodexMCPToolInputSchema(BaseModel):
    action: Literal["propose_change", "apply_change", "review_code", "explain_change"]

    # propose_change
    repo_root: Optional[str] = None
    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    objective: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None
    dry_run: bool = True

    # apply_change
    plan_id: Optional[str] = None
    strategy: Optional[Literal["local"]] = Field(default=None)
    branch: Optional[str] = None
    commit_message: Optional[str] = None

    # review_code
    paths: Optional[List[str]] = None
    rules: Optional[List[str]] = None


class CodexMCPTool(BaseTool):
    name: str = "CodexMCPTool"
    description: str = "Plan, apply, review and explain code changes via Codex MCP."
    args_schema = CodexMCPToolInputSchema
    client: Optional[CodexMCPClient] = None

    def __init__(self, base_url: Optional[str] = None, timeout_sec: Optional[int] = None) -> None:
        super().__init__()
        base_url_final = base_url or os.getenv("CODEX_MCP_URL", "http://localhost:8765/")
        timeout_final = int(timeout_sec or int(os.getenv("CODEX_TIMEOUT_SEC", "60")))
        self.client = CodexMCPClient(base_url_final, timeout_final)

    def _run(self, *args, **kwargs) -> Dict[str, Any]:
        # The tool is designed for structured inputs via args_schema + run()
        raise CodexMCPError("400_INVALID_INPUT", "CodexMCPTool requires structured inputs via run().")

    def run(self, inputs: CodexMCPToolInputSchema) -> Dict[str, Any]:
        try:
            if inputs.action == "propose_change":
                return self.client.propose_change(
                    repo_root=inputs.repo_root or os.getcwd(),
                    include=inputs.include or [],
                    exclude=inputs.exclude or [],
                    objective=inputs.objective or "",
                    context=inputs.context or [],
                    dry_run=inputs.dry_run,
                )
            if inputs.action == "apply_change":
                return self.client.apply_change(
                    plan_id=inputs.plan_id or "",
                    strategy=inputs.strategy or "local",
                    branch=inputs.branch or "feature/codex-mcp-apply",
                    commit_message=inputs.commit_message or "chore(codex): apply planned changes",
                )
            if inputs.action == "review_code":
                return self.client.review_code(
                    paths=inputs.paths or [],
                    rules=inputs.rules or [],
                )
            if inputs.action == "explain_change":
                return self.client.explain_change(
                    plan_id=inputs.plan_id or "",
                )
        except CodexMCPError:
            raise
        except Exception as e:  # safety net
            raise CodexMCPError("500_CODEX_EXECUTION_ERROR", f"Unexpected error: {e}") from e

        raise CodexMCPError("400_INVALID_INPUT", f"Unknown action: {inputs.action}")
