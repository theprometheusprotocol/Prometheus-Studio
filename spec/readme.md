# Codex MCP Adapter — Spec Reference

This folder tracks the interface contract used by Prometheus Studio to talk to the Codex MCP server.

## Documents

- **Contract (human-readable):**  
  [`codex_mcp_adapter_contract_v_1.md`](https://github.com/theprometheusprotocol/openai-codex-mcp/blob/d0f041450868c25dc900061cf943adc8a6ad3c44/spec/codex_mcp_adapter_contract_v_1.md)  
  Defines the stable interface (goals, request/response schemas, error codes, guardrails).

- **Manifest (machine-readable):**  
  [`openai_codex_mcp_with_adapter.json`](https://github.com/theprometheusprotocol/openai-codex-mcp/blob/d0f041450868c25dc900061cf943adc8a6ad3c44/spec/openai_codex_mcp_with_adapter.json)  
  JSON-RPC manifest implementing the contract for runtime discovery.

## Versioning

- **Contract version:** v1  
- **Manifest version:** aligned with contract v1 (commit `d0f0414`).

## Usage

Prometheus Studio tools that integrate Codex must conform to this contract.  
The MCP server is expected to expose methods:

- `propose_change`  
- `apply_change`  
- `review_code`  
- `explain_change`

Errors follow the canonical codes defined in the contract spec.
