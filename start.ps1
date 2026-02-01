param(
  [switch]$Debug,
  [string]$Config = "mcp_proxy_bridge.toml"
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"

$env:MCP_API_KEY = $env:MCP_API_KEY
if (-not $env:MCP_API_KEY) {
  Write-Host "MCP_API_KEY is not set. Set it before running." -ForegroundColor Yellow
}

$cmd = @("$root\mcp_proxy_bridge.py", "--config", $Config)
if ($Debug) { $cmd += "--debug" }

& $python @cmd
