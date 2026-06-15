---
name: entry-point-analyzer
description: "Analyzes codebases to identify external entry points for security auditing. Detects externally callable functions (web APIs, CLI commands, IPC handlers, exported library APIs) that change state, categorizes them by access level, and generates structured audit reports."
allowed-tools: Read Grep Glob Bash
---

# Entry Point Analyzer

Systematically identify all **externally reachable** entry points in a codebase to guide security audits.

## When to Use

Use this skill when:
- Starting a security audit to map the attack surface
- Asked to find entry points, external functions, or audit flows
- Analyzing access control patterns across the codebase
- Identifying privileged operations and role-restricted functions
- Building an understanding of which entry points can affect system state

## When NOT to Use

Do NOT use this skill for:
- Vulnerability detection (use domain-specific audit or fp-check)
- Writing exploit PoCs
- Code quality or performance analysis
- Analyzing read-only/view-only entry points (this skill focuses on state-changing surface)

## Scope: State-Changing Entry Points Only

This skill focuses on entry points that can modify system state. **Read-only entry points are excluded** unless they leak sensitive information critical for the audit context.

### Entry Point Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **Web APIs** | HTTP/RPC endpoints handling external requests | REST endpoints, gRPC methods, GraphQL resolvers, WebSocket handlers |
| **System Software** | CLI, daemon, IPC entry points | CLI commands, signal handlers, Unix sockets, D-Bus methods |
| **Library APIs** | Exported/public API surface | Public functions, plugin hooks, callback registrations, serialization handlers |
| **Integration** | Message/event-driven entry points | MQ consumers, webhook receivers, event listeners, cron tasks |

### Why Exclude Read-Only?

Pure read operations (database queries, data fetches, getters) do not directly cause state corruption or privilege escalation. While they may leak information, the primary audit focus is on entry points that can **change system state**. Information leakage from read-only endpoints should be assessed separately.

## Workflow

1. **Detect Framework / Language** — Identify the tech stack from file extensions, config files, and dependency manifests
2. **Load Reference** — Load the appropriate reference file for the detection category
3. **Locate Entry Points** — Scan for entry point registrations, route definitions, and exported symbols
4. **Classify Access** — Categorize each entry point by access level
5. **Generate Report** — Output structured markdown report

## Framework Detection

| Files / Indicators | Likely Tech | Reference |
|--------------------|-------------|-----------|
| `requirements.txt`, `Pipfile`, `pyproject.toml` | Python (web/system) | [web-apis.md]({baseDir}/references/web-apis.md) |
| `package.json`, `tsconfig.json` | Node.js / TypeScript | [web-apis.md]({baseDir}/references/web-apis.md) |
| `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle` | Rust / Go / Java | [web-apis.md]({baseDir}/references/web-apis.md) |
| `*.csproj`, `*.sln` | .NET | [web-apis.md]({baseDir}/references/web-apis.md) |
| `main.go`, `cmd/` directory | Go CLI | [system-software.md]({baseDir}/references/system-software.md) |
| `*.rs` with `clap`, `*.py` with `click`/`argparse` | CLI tool | [system-software.md]({baseDir}/references/system-software.md) |
| `lib/`, `src/lib.rs`, `__init__.py` with exports | Library | [library-apis.md]({baseDir}/references/library-apis.md) |
| `Dockerfile`, `docker-compose.yml` | Service deployment | Cross-check all categories |

Load the appropriate reference file(s) based on detected tech before analysis.

## Access Classification

Classify each state-changing entry point into one of these categories:

### 1. Public (Unrestricted)
Entry points callable by anyone without authentication or authorization.

### 2. Authenticated
Entry points that require a valid authenticated session or credential.

### 3. Role-Restricted
Entry points limited to specific roles or permissions. Common role patterns:
- **Admin**: `admin`, `owner`, `root`, `sysadmin`, `superuser`
- **Operator**: `operator`, `keeper`, `maintainer`, `relayer`
- **Finance**: `finance`, `treasury`, `accountant`, `paymaster`
- **Security**: `guardian`, `security`, `auditor`
- **Read-only**: `viewer`, `reader`, `observer`, `monitor`
- When role is ambiguous, flag as **"Restricted (review required)"** with the restriction pattern noted

### 4. Internal-Only
Entry points only callable by internal components, not external callers.

### Review Required (Cross-Cutting)
Entry points with ambiguous or custom access control patterns that need manual verification.

## Output Format

Generate a markdown report with this structure:

```markdown
# Entry Point Analysis: [Project Name]

**Analyzed**: [timestamp]
**Scope**: [directories analyzed or "full codebase"]
**Technology**: [detected languages/frameworks]
**Focus**: State-changing entry points only

## Summary

| Category | Count |
|----------|-------|
| Public (Unrestricted) | X |
| Authenticated | X |
| Role-Restricted | X |
| Internal-Only | X |
| Review Required | X |
| **Total** | **X** |

---

## Public Entry Points (Unrestricted)

State-changing entry points with no access control — prioritize for attack surface analysis.

| Entry Point | Type | File | Notes |
|-------------|------|------|-------|
| `POST /api/users` | Web API | `routes/users.go:L42` | Creates users (no auth) |

---

## Authenticated Entry Points

| Entry Point | Type | File | Auth Method |
|-------------|------|------|-------------|
| `POST /api/transfer` | Web API | `routes/finance.go:L15` | JWT required |

---

## Role-Restricted Entry Points

### Admin
| Entry Point | Type | File | Restriction |
|-------------|------|------|-------------|
| `DELETE /api/users/:id` | Web API | `routes/admin.go:L30` | `admin` role |

### Operator
| Entry Point | Type | File | Restriction |
|-------------|------|------|-------------|

### Other Roles
| Entry Point | Type | File | Restriction | Role |
|-------------|------|------|-------------|------|

---

## Internal-Only Entry Points

Internally exposed entry points — useful for understanding trust boundaries.

| Entry Point | Type | File | Expected Caller |
|-------------|------|------|-----------------|
| `processMessage(msg)` | IPC | `internal/worker.go:L80` | Internal worker pool |

---

## Review Required

Entry points with ambiguous access control that need manual verification.

| Entry Point | Type | File | Pattern | Why Review |
|-------------|------|------|---------|------------|
| `execCommand(cmd)` | CLI | `cli/execute.go:L55` | `if authorized[user]` | Dynamic authorization list |

---

## Entry Points by Category

### Web APIs
| Method | Path | Handler | Auth | File |
|--------|------|---------|------|------|
| GET | `/api/health` | `healthCheck` | None | `server/handler.go:L10` |
| POST | `/api/transfer` | `transferFunds` | JWT | `server/handler.go:L25` |

### CLI Commands
| Command | Description | Auth | File |
|---------|-------------|------|------|
| `tool admin reset` | Reset system | Root | `cmd/admin.go:L8` |

---

## Files Analyzed

- `path/to/file1.go` (X state-changing entry points)
- `path/to/file2.py` (X state-changing entry points)
```

## Filtering

When user specifies a directory filter:
- Only analyze files within that path
- Note the filter in the report header
- Example: "Analyze only `src/web/`" → scope = `src/web/`

## Tooling Integration

### grep-Based Discovery

For manual analysis, use grep to find entry point patterns:

```bash
# Find HTTP route registrations
rg 'app\.(get|post|put|delete|patch)\(' --type-add 'web:*.{py,js,ts,go,java}'
rg '@(GetMapping|PostMapping|RequestMapping)'
rg 'router\.(GET|POST|PUT|DELETE)'

# Find CLI command registrations
rg '@click\.(command|group)' --type py
rg 'cobra\.Command' --type go
rg 'parser\.add_argument' --type py

# Find exported/library functions
rg '^pub fn' --type rust
rg '^export (function|default|class)' --type ts
rg '^def ' --type py --glob '!test_*'

# Find deserialization sinks
rg 'pickle\.loads|yaml\.load\(|ObjectInputStream|BinaryFormatter\.Deserialize'
```

### Language-Specific Tools

| Language | Tool | How to Use |
|----------|------|------------|
| **Python** | `ast` module | `python3 -c "import ast; ast.parse(open('file.py').read())"` + walk nodes |
| **JavaScript** | `@babel/parser` | Parse and extract exports, route registrations |
| **Go** | `go doc` | List exported symbols: `go doc ./pkg/...` |
| **Rust** | `cargo doc --document-private-items` | Generate docs with all pub items |
| **Java** | `javap -public` | List public classes and methods from .class files |
| **.NET** | `dotnet list reference` | List assemblies; `ildasm` for exports |

## Analysis Guidelines

1. **Be thorough**: Don't skip files. Every state-changing entry point matters.
2. **Be conservative**: When uncertain about access level, flag for review rather than miscategorize.
3. **Skip read-only**: Exclude pure read/view endpoints unless information disclosure is in-scope.
4. **Note middleware**: If auth comes from global/group middleware rather than per-route, note it.
5. **Track dependency**: List all middleware/decorators/annotations applied to each entry point.
6. **Identify patterns**: Look for common patterns like:
   - Admin panels (often on separate ports or paths)
   - Health/status endpoints (often intentionally public)
   - Webhook receivers (auth may be via payload signature)
   - File upload/download endpoints
   - Configuration mutation endpoints
   - User management endpoints

## Rationalizations to Reject

When analyzing entry points, reject these shortcuts:
- "This endpoint looks standard" — Still classify it; standard endpoints can have missing auth
- "The middleware name is clear" — Verify the middleware's actual implementation
- "This is obviously admin-only" — Trace the actual restriction; "obvious" assumptions miss subtle bypasses
- "I'll skip background workers" — Workers process user data; always include them
- "It doesn't modify critical state" — Any state change can be exploited; include all non-read entry points
- "This CLI command is internal" — Check who can access the CLI (SSH, container exec, CI pipeline)

## Error Handling

If a file cannot be parsed:
1. Note it in the report under "Analysis Warnings"
2. Continue with remaining files
3. Suggest manual review for unparsable files
