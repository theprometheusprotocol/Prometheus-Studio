# app/tools/CodexMCPTool.py
import os
import json
import uuid
from typing import Literal, List, Dict, Any, Optional

import requests
from pydantic import BaseModel
from crewai.tools import BaseTool


class CodexMCPError(RuntimeError):
    def __init__(self, studio_code: str, message: str):
        super().__init__(f"{studio_code}: {message}")
        self.studio_code = studio_code
        self.message = message


def _map_mcp_error(err: Dict[str, Any]) -> CodexMCPError:
    code = err.get("code")
    msg = err.get("message", "Unknown Codex MCP error")

    if isinstance(code, int):
        # Fallback numeric mapping
        numeric_map = {
            -32602: "400_INVALID_INPUT",
            -32000: "500_CODEX_EXECUTION_ERROR",
        }
        studio_code = numeric_map.get(code, "500_CODEX_EXECUTION_ERROR")
    else:
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
        # Normalize: always post JSON-RPC to root "/"
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/"
        self.timeout = timeout_sec

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
        try:
            resp = requests.post(self.endpoint, json=body, timeout=self.timeout)
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

    # ---- Contract v1 methods ----

    def propose_change(
        self,
        goal: str,
        context: str,
        repoRef: Dict[str, Any],
        constraints: Dict[str, Any],
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        return self._rpc(
            "propose_change",
            {"goal": goal, "context": context, "repoRef": repoRef, "constraints": constraints, "dry_run": dry_run},
        )

    def apply_change(
        self,
        plan_id: str,
        goal: str,
        repoRef: Dict[str, Any],
        constraints: Dict[str, Any],
        run_checks: bool,
        open_pr: bool,
        branch_prefix: str,
        dry_run: bool,
    ) -> Dict[str, Any]:
        return self._rpc(
            "apply_change",
            {
                "plan_id": plan_id,
                "goal": goal,
                "repoRef": repoRef,
                "constraints": constraints,
                "run_checks": run_checks,
                "open_pr": open_pr,
                "branch_prefix": branch_prefix,
                "dry_run": dry_run,
            },
        )

    def review_code(self, target: Dict[str, Any], guidelines: List[Dict[str, Any]], severity_threshold: str = "warn") -> Dict[str, Any]:
        return self._rpc("review_code", {"target": target, "guidelines": guidelines, "severity_threshold": severity_threshold})

    def explain_change(self, target: Dict[str, Any], audience: str = "dev", max_words: int = 200) -> Dict[str, Any]:
        return self._rpc("explain_change", {"target": target, "audience": audience, "max_words": max_words})


# ---- Tool schema uses only Contract v1 fields ----

class CodexMCPToolInputSchema(BaseModel):
    action: Literal["propose_change", "apply_change", "review_code", "explain_change"]

    # propose_change
    goal: Optional[str] = None
    context: Optional[str] = None
    repoRef: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    dry_run: bool = True

    # apply_change
    plan_id: Optional[str] = None
    run_checks: Optional[bool] = True
    open_pr: Optional[bool] = False
    branch_prefix: Optional[str] = "feature/"

    # review_code / explain_change
    target: Optional[Dict[str, Any]] = None
    guidelines: Optional[List[Dict[str, Any]]] = None
    severity_threshold: Optional[str] = "warn"
    audience: Optional[str] = "dev"
    max_words: Optional[int] = 200


class CodexMCPTool(BaseTool):
    name: str = "CodexMCPTool"
    description: str = "Plan, apply, review and explain code changes via Codex MCP."
    args_schema = CodexMCPToolInputSchema
    client: Optional[CodexMCPClient] = None

    def __init__(self, base_url: Optional[str] = None, timeout_sec: Optional[int] = None) -> None:
        super().__init__()
        base_url_final = (base_url or os.getenv("CODEX_MCP_URL", "http://localhost:8765")).rstrip("/")
        timeout_final = int(timeout_sec or int(os.getenv("CODEX_TIMEOUT_SEC", "60")))
        self.client = CodexMCPClient(base_url_final, timeout_final)

    def _run(self, *args, **kwargs) -> Dict[str, Any]:
        raise CodexMCPError("400_INVALID_INPUT", "CodexMCPTool requires structured inputs via run().")

    def run(self, inputs: CodexMCPToolInputSchema) -> Dict[str, Any]:
        try:
            data = normalize_codex_input(inputs)
            if data.action == "propose_change":
                return self.client.propose_change(
                    goal=data.goal or "",
                    context=data.context or "",
                    repoRef=data.repoRef or {"mode": "local", "repo_path": os.getcwd()},
                    constraints=data.constraints or {},
                    dry_run=data.dry_run,
                )

            if data.action == "apply_change":
                return self.client.apply_change(
                    plan_id=data.plan_id or "",
                    goal=data.goal or "",
                    repoRef=data.repoRef or {"mode": "local", "repo_path": os.getcwd()},
                    constraints=data.constraints or {},
                    run_checks=bool(data.run_checks),
                    open_pr=bool(data.open_pr),
                    branch_prefix=data.branch_prefix or "feature/",
                    dry_run=data.dry_run,
                )

            if data.action == "review_code":
                return self.client.review_code(
                    target=data.target or {},
                    guidelines=data.guidelines or [],
                    severity_threshold=data.severity_threshold or "warn",
                )

            if data.action == "explain_change":
                return self.client.explain_change(
                    target=data.target or {},
                    audience=data.audience or "dev",
                    max_words=int(data.max_words or 200),
                )

        except CodexMCPError:
            raise
        except Exception as e:
            raise CodexMCPError("500_CODEX_EXECUTION_ERROR", f"Unexpected error: {e}") from e

        raise CodexMCPError("400_INVALID_INPUT", f"Unknown action: {getattr(inputs, 'action', None)}")


def normalize_codex_input(obj: Any) -> CodexMCPToolInputSchema:
    """Normalize tool input into CodexMCPToolInputSchema.
    Accepts Pydantic model, dict, JSON string, or single-item list. Raises CodexMCPError on invalid input.
    """
    if isinstance(obj, CodexMCPToolInputSchema):
        return obj
    if isinstance(obj, BaseModel):
        data = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
        return CodexMCPToolInputSchema(**data)
    if isinstance(obj, dict):
        return CodexMCPToolInputSchema(**obj)
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
        except Exception:
            raise CodexMCPError("400_INVALID_INPUT", "Expected single JSON object for tool input.")
        return normalize_codex_input(parsed)
    if isinstance(obj, list) and len(obj) == 1:
        return normalize_codex_input(obj[0])
    raise CodexMCPError("400_INVALID_INPUT", "Expected single JSON object for tool input.")
