# Entry Point Analyzer

A plugin for systematically identifying **state-changing entry points** in any codebase to guide security audits.

## Purpose

When auditing a codebase, examining each file or function individually is inefficient. What auditors need is to start from **entry points**—the externally reachable functions that represent the attack surface. This plugin automates the identification and classification of state-changing entry points across four categories:

- **Web APIs** — REST endpoints, gRPC methods, GraphQL resolvers, WebSocket handlers
- **System Software** — CLI commands, daemon handlers, IPC listeners, signal handlers
- **Library APIs** — Exported/public functions, plugin hooks, deserialization sinks
- **Integration** — Message queue consumers, webhook receivers, event listeners, cron tasks

## Supported Technologies

| Category | Technologies |
|----------|-------------|
| **Web Frameworks** | Express, FastAPI, Flask, Django, Spring Boot, ASP.NET Core, Gin, Echo, Actix-web, Axum, Phoenix, NestJS, Fastify, Koa |
| **RPC** | gRPC, Thrift, dubbo, JSON-RPC, tRPC |
| **CLI Frameworks** | argparse, click, typer (Python); cobra, urfave/cli (Go); clap (Rust); picocli (Java); Commander.js, Yargs (Node) |
| **IPC** | Unix sockets, D-Bus, named pipes, shared memory, Windows messages, COM |
| **Languages** | Python, JavaScript/TypeScript, Go, Rust, Java, C#, C/C++, Ruby, PHP, Elixir |

## Access Classifications

| Level | Meaning |
|-------|---------|
| **Public (Unrestricted)** | No authentication required; highest audit priority |
| **Authenticated** | Requires valid credentials but no specific role |
| **Role-Restricted** | Limited to specific roles/permissions |
| **Review Required** | Ambiguous access patterns needing manual verification |
| **Internal-Only** | Not externally callable (private methods, internal IPC) |

## Output

Generates a structured markdown report with:
- Summary table of entry point counts by category
- Detailed tables for each access level
- Entry point signatures with file:line references
- Authentication/authorization patterns detected
- List of analyzed files

## Usage

Trigger the skill with requests like:
- "Analyze the entry points in this codebase"
- "Find all external functions and access levels"
- "List audit flows for src/api/"
- "What privileged operations exist in this project?"

## Directory Filtering

Specify a subdirectory to limit scope:
- "Analyze only `src/web/`"
- "Find entry points in `cmd/`"

## Installation

```
/plugin install entry-point-analyzer
```

## Components

### Skills

| Skill | Description |
|-------|-------------|
| [entry-point-analyzer](skills/entry-point-analyzer/SKILL.md) | Generic entry point detection for security audits |

### References

| File | Purpose |
|------|---------|
| [web-apis.md](skills/entry-point-analyzer/references/web-apis.md) | HTTP/RPC/WebSocket entry point detection patterns |
| [system-software.md](skills/entry-point-analyzer/references/system-software.md) | CLI, daemon, IPC entry point detection patterns |
| [library-apis.md](skills/entry-point-analyzer/references/library-apis.md) | Library exports, plugin hooks, deserialization sinks |
| [access-control-patterns.md](skills/entry-point-analyzer/references/access-control-patterns.md) | Cross-language access control patterns and detection |

## License

See LICENSE.txt for terms.
