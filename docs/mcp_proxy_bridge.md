# mcp_proxy_bridge 多服务代理

这是一个多服务 MCP 兼容代理，用于在 Codex 与旧版 MCP 服务之间做协议兼容（版本降级/回写、头部补齐、会话兼容、工具列表缓存）。

## 1) 启动

```bash
pip install aiohttp
python mcp_proxy_bridge.py --config mcp_proxy_bridge.toml
python mcp_proxy_bridge.py --config mcp_proxy_bridge.toml --debug
```

## 2) 配置文件

`mcp_proxy_bridge.toml` 示例：

```toml
[server]
listen_host = "127.0.0.1"
listen_port = 8765

[services.web-reader]
upstream_url = "https://open.bigmodel.cn/api/mcp/web_reader/mcp"

[services.web-search-prime]
upstream_url = "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp"

[services.zread]
upstream_url = "https://open.bigmodel.cn/api/mcp/zread/mcp"

# 可选：为单个服务指定版本/头部/行为（放在对应 service 下）
# target_protocol_version = "2024-11-05"
# client_protocol_version = "2025-06-18"
# accept = "application/json, text/event-stream"
# content_type = "application/json"
# inject_tools_list = true
# notify_tools_changed = true
```

### 可选字段（每个 service）
- `target_protocol_version`：服务端支持的版本（默认 `2024-11-05`）
- `client_protocol_version`：Codex 期望的版本（默认 `2025-06-18`）
- `accept`：默认 `application/json, text/event-stream`
- `content_type`：默认 `application/json`
- `Authorization` 由 Codex 端传入（代理不处理鉴权）
- `inject_tools_list`：是否缓存并注入 tools/list（默认 true）
- `notify_tools_changed`：是否触发 tools/list_changed（默认 true）

## 3) Codex 配置

在 `~/.codex/config.toml` 里把 URL 指向代理（必须带服务名路径）：

```toml
[mcp_servers.web-reader]
url = "http://127.0.0.1:8765/mcp/web-reader"

[mcp_servers.web-reader.http_headers]
Accept = "application/json, text/event-stream"
Content-Type = "application/json"
Authorization = "Bearer YOUR_TOKEN"

[mcp_servers.web-search-prime]
url = "http://127.0.0.1:8765/mcp/web-search-prime"

[mcp_servers.web-search-prime.http_headers]
Accept = "application/json, text/event-stream"
Content-Type = "application/json"
Authorization = "Bearer YOUR_TOKEN"

[mcp_servers.zread]
url = "http://127.0.0.1:8765/mcp/zread"

[mcp_servers.zread.http_headers]
Accept = "application/json, text/event-stream"
Content-Type = "application/json"
Authorization = "Bearer YOUR_TOKEN"
```

> 注意：鉴权放在 Codex 的 `config.toml`，代理只透传 `Authorization`。

### Codex 端鉴权（优先 bearer_token_env_var）

方式 A：bearer_token_env_var（推荐）
```toml
[mcp_servers.web-reader]
url = "http://127.0.0.1:8765/mcp/web-reader"
bearer_token_env_var = "MCP_API_KEY"
```
环境变量中设置：
```
MCP_API_KEY=你的纯token
```

方式 B：明文写入 `Authorization`

方式 C：env_http_headers（自定义 Authorization）
```toml
[mcp_servers.web-reader]
url = "http://127.0.0.1:8765/mcp/web-reader"
env_http_headers = { "Authorization" = "MCP_API_AUTH" }
```
环境变量中设置：
```
MCP_API_AUTH=Bearer <token>
```

### 规范要点

- URL 必须是 `http://127.0.0.1:8765/mcp/<服务名>`
- `Accept` 必须包含 `text/event-stream`
- 改完配置后重启 codex

## 4) 验证

- `/mcp` 查看工具列表
- 调用工具如 `webReader`

## 5) 常见问题

- 若工具列表为空，打开 `debug = true` 查看是否有 `cached tools/list` 日志。
- 若握手失败，检查 `auth_header` 是否正确。
