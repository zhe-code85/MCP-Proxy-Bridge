# Change: Initialize MCP Proxy Bridge Specs

## Why
We need a clear, spec-driven baseline for the MCP proxy bridge so behavior is stable and maintainable.

## What Changes
- Define the initial capability specification for the MCP proxy bridge.
- Document routing, protocol rewrite, header normalization, session handling, and tools caching behavior.

## Impact
- Affected specs: mcp-proxy-bridge
- Affected code: mcp_proxy_bridge.py, mcp_proxy_bridge.toml, docs/mcp_proxy_bridge.md
