# Project Context

## Purpose
Provide a lightweight MCP proxy bridge that makes Codex compatible with legacy MCP servers by rewriting protocol versions, normalizing headers/session IDs, and caching tool lists.

## Tech Stack
- Python 3.11
- aiohttp
- tomllib

## Project Conventions

### Code Style
- Python typing hints for public helpers and dataclasses
- snake_case for functions/variables
- UTF-8 without BOM for config and docs

### Architecture Patterns
- Single-process HTTP proxy
- Per-service configuration and state
- Minimal dependencies and streaming-first I/O

### Testing Strategy
- Manual verification with Codex/CLI
- Debug logging for request/response tracing

### Git Workflow
- main branch
- Small, atomic commits with descriptive messages

## Domain Context
- MCP Streamable HTTP
- JSON-RPC initialize/tools/list flows
- Session ID propagation (Mcp-Session-Id)

## Important Constraints
- Keep implementation minimal and predictable
- Avoid adding heavy dependencies
- Preserve streaming responses where possible

## External Dependencies
- BigModel MCP endpoints
- Codex MCP client behavior
