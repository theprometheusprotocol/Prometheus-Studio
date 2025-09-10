import os
from app.tools.CodexMCPTool import CodexMCPClient


def main():
    url = os.getenv("CODEX_MCP_URL", "http://localhost:8765/")
    timeout = int(os.getenv("CODEX_TIMEOUT_SEC", "60"))
    client = CodexMCPClient(base_url=url, timeout_sec=timeout)
    result = client.propose_change(
        repo_root=os.getcwd(),
        include=["spec/**/*.md"],
        exclude=["**/.git/**", "**/__pycache__/**"],
        objective="Plan-only Codex wiring",
        context=[],
        dry_run=True,
    )
    assert result.get("plan_id"), "Expected non-empty plan_id"
    assert result.get("preview_diff"), "Expected non-empty preview_diff"
    print(f"plan_id={result['plan_id']}")
    print(f"preview_diff_len={len(result['preview_diff'])}")


if __name__ == "__main__":
    main()

