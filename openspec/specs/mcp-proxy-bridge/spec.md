## Purpose
Provide a compatibility proxy that bridges Codex with legacy MCP servers by normalizing protocol versions, headers, session IDs, and tools listings.
## Requirements
### Requirement: Service routing
The system SHALL route requests to `/mcp/{service}` based on the configured upstream URL for that service.

#### Scenario: Unknown service
- **WHEN** a request is received for an unconfigured service name
- **THEN** the system returns HTTP 404

#### Scenario: Known service
- **WHEN** a request is received for a configured service name
- **THEN** the system forwards it to the configured upstream URL

### Requirement: Protocol version rewrite
The system SHALL rewrite the MCP initialize request protocol version to the configured target version and rewrite the initialize response protocol version to the configured client version.

#### Scenario: Rewrite initialize request
- **WHEN** the client sends an initialize request
- **THEN** the upstream receives the target protocol version

#### Scenario: Rewrite initialize response
- **WHEN** the upstream responds to initialize
- **THEN** the client receives the configured client protocol version

### Requirement: Header normalization
The system SHALL enforce configured Accept and Content-Type headers and forward client Authorization headers unchanged.

#### Scenario: Enforce Accept and Content-Type
- **WHEN** a request is proxied
- **THEN** the configured Accept and Content-Type headers are present

#### Scenario: Authorization passthrough
- **WHEN** the client sends an Authorization header
- **THEN** the upstream receives the same Authorization header

### Requirement: Session ID propagation
The system SHALL normalize Mcp-Session-Id/mcp-session-id and propagate the session ID to follow-up requests.

#### Scenario: Track session ID
- **WHEN** the upstream returns a session ID header
- **THEN** the system stores that session ID for the service

#### Scenario: Inject session ID
- **WHEN** a follow-up request is sent without a session ID
- **THEN** the system injects the stored session ID

### Requirement: Tools list caching and notification
The system SHALL optionally cache tools/list results and notify clients of tool list changes.

#### Scenario: Cache tools/list
- **WHEN** initialize completes and tools caching is enabled
- **THEN** the system requests tools/list and caches the result

#### Scenario: tools/list_changed notification
- **WHEN** tools caching is enabled
- **THEN** the system emits tools/list_changed notification

#### Scenario: Serve cached tools/list
- **WHEN** the client requests tools/list and a cache is available
- **THEN** the system returns the cached tools list

### Requirement: CLI configuration
The system SHALL accept a config path and a debug flag via CLI.

#### Scenario: Custom config path
- **WHEN** the CLI is invoked with --config
- **THEN** the system loads configuration from that path

#### Scenario: Debug logging
- **WHEN** the CLI is invoked with --debug
- **THEN** the system emits debug logs

