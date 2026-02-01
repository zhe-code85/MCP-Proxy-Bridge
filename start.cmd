@echo off
setlocal

set ROOT=%~dp0
set CONFIG=mcp_proxy_bridge.toml
set DEBUG=

:parse
if "%~1"=="" goto run
if /I "%~1"=="--debug" set DEBUG=--debug
if /I "%~1"=="--config" set CONFIG=%~2& shift
shift
goto parse

:run
if "%MCP_API_KEY%"=="" echo MCP_API_KEY is not set. Set it before running.
python "%ROOT%mcp_proxy_bridge.py" --config "%ROOT%%CONFIG%" %DEBUG%
endlocal
