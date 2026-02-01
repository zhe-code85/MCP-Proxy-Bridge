import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import web, ClientSession


@dataclass
class ServiceConfig:
    name: str
    upstream_url: str
    target_protocol_version: str
    client_protocol_version: str
    accept: str = "application/json, text/event-stream"
    content_type: str = "application/json"
    inject_tools_list: bool = True
    notify_tools_changed: bool = True


@dataclass
class ServiceState:
    last_session_id: str | None = None
    tools_cache: list[dict[str, Any]] | None = None


@dataclass
class ProxyConfig:
    listen_host: str = "127.0.0.1"
    listen_port: int = 8765
    debug: bool = False
    services: dict[str, ServiceConfig] = field(default_factory=dict)


def _log(cfg: ProxyConfig, msg: str) -> None:
    if cfg.debug:
        print(msg)


def load_config(path: Path) -> ProxyConfig:
    import tomllib

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    cfg = ProxyConfig()
    server = data.get("server", {})
    cfg.listen_host = server.get("listen_host", cfg.listen_host)
    cfg.listen_port = int(server.get("listen_port", cfg.listen_port))

    services = data.get("services", {})
    for name, svc in services.items():
        cfg.services[name] = ServiceConfig(
            name=name,
            upstream_url=svc["upstream_url"],
            target_protocol_version=svc.get("target_protocol_version", "2024-11-05"),
            client_protocol_version=svc.get("client_protocol_version", "2025-06-18"),
            accept=svc.get("accept", "application/json, text/event-stream"),
            content_type=svc.get("content_type", "application/json"),
            inject_tools_list=bool(svc.get("inject_tools_list", True)),
            notify_tools_changed=bool(svc.get("notify_tools_changed", True)),
        )
    return cfg


def _norm_session_id(headers: dict[str, str]) -> str | None:
    return headers.get("mcp-session-id") or headers.get("Mcp-Session-Id")


async def fetch_tools(svc: ServiceConfig, headers: dict[str, str]) -> list[dict[str, Any]] | None:
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    async with ClientSession() as session:
        async with session.post(svc.upstream_url, headers=headers, json=payload) as resp:
            body = await resp.read()
            text = body.decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.startswith("data:"):
                    try:
                        msg = json.loads(line[5:].strip())
                        res = msg.get("result", {})
                        tools = res.get("tools")
                        if isinstance(tools, list):
                            return tools
                    except Exception:
                        continue
    return None


def make_handler(cfg: ProxyConfig, state_map: dict[str, ServiceState]):
    async def handle(request: web.Request) -> web.Response:
        svc_name = request.match_info.get("name")
        if not svc_name or svc_name not in cfg.services:
            return web.Response(status=404, text="unknown service")

        svc = cfg.services[svc_name]
        state = state_map.setdefault(svc_name, ServiceState())

        method = request.method
        headers = dict(request.headers)
        data = await request.read()

        _log(cfg, f"[mcp_proxy_bridge:{svc_name}] request {method} {request.path} len={request.headers.get('Content-Length','-')}")

        # Normalize headers
        headers.pop("Host", None)
        headers.pop("Content-Length", None)
        headers.pop("Accept-Encoding", None)

        # Force Accept/Content-Type
        headers["Accept"] = svc.accept
        headers["Content-Type"] = svc.content_type
        # Authorization is passed through from Codex config.toml

        rpc_method = None
        if method == "POST" and data:
            try:
                obj = json.loads(data.decode("utf-8"))
                rpc_method = obj.get("method")
                if rpc_method == "initialize":
                    params = obj.setdefault("params", {})
                    params["protocolVersion"] = svc.target_protocol_version
                    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
                    _log(cfg, f"[mcp_proxy_bridge:{svc_name}] patched protocolVersion -> {svc.target_protocol_version}")
            except Exception:
                _log(cfg, f"[mcp_proxy_bridge:{svc_name}] failed to parse JSON body; passing through")

        # Force session id on follow-up requests
        if state.last_session_id and (method != "POST" or (rpc_method and rpc_method != "initialize")):
            headers["mcp-session-id"] = state.last_session_id
            headers["Mcp-Session-Id"] = state.last_session_id

        async with ClientSession() as session:
            async with session.request(method, svc.upstream_url, headers=headers, data=data) as resp:
                resp_headers = dict(resp.headers)
                for h in ["Transfer-Encoding", "Content-Encoding", "Content-Length", "Connection"]:
                    resp_headers.pop(h, None)

                # Track session id
                sid = _norm_session_id(resp_headers)
                if sid:
                    state.last_session_id = sid
                    _log(cfg, f"[mcp_proxy_bridge:{svc_name}] session-id={sid}")

                # Normalize session header key
                if "mcp-session-id" not in resp_headers and "Mcp-Session-Id" in resp_headers:
                    resp_headers["mcp-session-id"] = resp_headers["Mcp-Session-Id"]

                # Special handling for initialized notifications
                if rpc_method == "notifications/initialized":
                    return web.Response(status=204, headers=resp_headers)

                content_type = resp_headers.get("Content-Type", "")
                if rpc_method == "initialize":
                    # Stream initialize response and rewrite protocolVersion on the fly
                    stream = web.StreamResponse(status=resp.status, headers=resp_headers)
                    await stream.prepare(request)
                    _log(cfg, f"[mcp_proxy_bridge:{svc_name}] initialize -> client protocolVersion={svc.client_protocol_version}")

                    buffer = b""
                    try:
                        async for chunk in resp.content.iter_chunked(8192):
                            buffer += chunk
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                if line.startswith(b"data:"):
                                    try:
                                        payload = json.loads(line[5:].strip())
                                        if isinstance(payload, dict) and "result" in payload:
                                            res = payload.get("result") or {}
                                            if isinstance(res, dict) and res.get("protocolVersion"):
                                                res["protocolVersion"] = svc.client_protocol_version
                                                payload["result"] = res
                                                line = b"data:" + json.dumps(payload, separators=(",", ":")).encode("utf-8")
                                    except Exception:
                                        pass
                                await stream.write(line + b"\n")
                        if buffer:
                            await stream.write(buffer)
                    except Exception:
                        pass

                    if svc.inject_tools_list:
                        try:
                            state.tools_cache = await fetch_tools(svc, headers)
                            if state.tools_cache is not None:
                                _log(cfg, f"[mcp_proxy_bridge:{svc_name}] cached tools/list with {len(state.tools_cache)} tools")
                        except Exception:
                            pass

                    if svc.notify_tools_changed:
                        try:
                            notif = {"jsonrpc": "2.0", "method": "notifications/tools/list_changed", "params": {}}
                            await stream.write(b"event:message\n")
                            await stream.write(b"data:" + json.dumps(notif, separators=(",", ":")).encode("utf-8") + b"\n\n")
                            _log(cfg, f"[mcp_proxy_bridge:{svc_name}] injected notifications/tools/list_changed")
                        except Exception:
                            pass

                    return stream

                if "text/event-stream" in content_type:
                    stream = web.StreamResponse(status=resp.status, headers=resp_headers)
                    await stream.prepare(request)
                    try:
                        async for chunk in resp.content.iter_chunked(8192):
                            await stream.write(chunk)
                    except Exception:
                        pass
                    return stream

                # Non-streaming response: buffer and return
                body = await resp.read()
                if rpc_method == "tools/list" and state.tools_cache is not None:
                    resp_msg = {"jsonrpc": "2.0", "id": 2, "result": {"tools": state.tools_cache}}
                    body = (
                        b"event:message\n"
                        + b"data:"
                        + json.dumps(resp_msg, separators=(",", ":")).encode("utf-8")
                        + b"\n\n"
                    )
                    resp_headers["Content-Type"] = "text/event-stream;charset=UTF-8"
                    _log(cfg, f"[mcp_proxy_bridge:{svc_name}] served cached tools/list ({len(state.tools_cache)} tools)")
                return web.Response(status=resp.status, headers=resp_headers, body=body)

    return handle


def main() -> None:
    parser = argparse.ArgumentParser(description="mcp_proxy_bridge")
    parser.add_argument("--config", default="mcp_proxy_bridge.toml", help="Path to mcp_proxy_bridge.toml")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    if args.debug:
        cfg.debug = True
    state_map: dict[str, ServiceState] = {}

    app = web.Application()
    app.router.add_route("*", "/mcp/{name}", make_handler(cfg, state_map))

    web.run_app(app, host=cfg.listen_host, port=cfg.listen_port)


if __name__ == "__main__":
    main()
