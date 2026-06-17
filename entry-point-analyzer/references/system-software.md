# System Software Entry Point Detection

## CLI Entry Points

CLI tools expose entry points through command/subcommand parsers, flag definitions, and main function dispatch.

### Framework-Specific Patterns

| Framework/Language | Pattern | Example |
|--------------------|---------|---------|
| **argparse (Python)** | `parser.add_argument('--flag')` + `args.func()` | Direct dispatch from parsed args |
| **click (Python)** | `@click.command()` + `@click.option()` | Decorator-based, nested groups |
| **Typer (Python)** | Function-based CLI (type hints) | `def main(name: str, count: int = 1):` |
| **cobra (Go)** | `rootCmd.AddCommand(subCmd)` | `var cmdRun = &cobra.Command{Use: "run", Run: func(...)}` |
| **urfave/cli (Go)** | `app.Commands = []cli.Command{...}` | `Action: func(ctx *cli.Context) error` |
| **clap (Rust)** | `#[derive(Parser)] struct Args` | `#[command(subcommand)] enum Commands` |
| **picocli (Java)** | `@CommandLine.Command` + `@CommandLine.Option` | `class Run implements Runnable { @CommandLine.Parameters ... }` |
| **Commander.js** | `program.command('cmd').action(handler)` | `program.command('transfer').action(transferHandler)` |
| **Yargs (Node.js)** | `yargs.command('cmd', desc, builder, handler)` | `.command('run', 'run command', (yargs) => {...}, (argv) => {...})` |
| **System.CommandLine (.NET)** | `rootCommand.AddCommand(subCommand)` | `new Command("run", "Description")` |
| **manual parse** | `os.Args` / `sys.argv` / `$args` parsing | Raw argument index access |

### CLI Entry Point Categories

| Category | Example |
|----------|---------|
| **Root commands** | `tool run`, `tool start`, `tool deploy` |
| **Admin commands** | `tool admin reset`, `tool db migrate` |
| **Configuration commands** | `tool config set`, `tool config show` |
| **Daemon/Server commands** | `tool serve`, `tool daemon`, `tool start --daemon` |
| **Data manipulation** | `tool import`, `tool export`, `tool transfer` |
| **Maintenance** | `tool cleanup`, `tool backup`, `tool restore` |

## Service/Daemon Entry Points

Background services and daemons have entry points through signal handlers, configuration-driven lifecycle hooks, and worker loops.

### Common Patterns

| Pattern | Detection | Example |
|---------|-----------|---------|
| **Main loop** | `while(running)` / `for` + sleep | `while (!shutdown) { process_events() }` |
| **Signal handler** | `signal(SIGINT, handler)`, `signal.signal()` | `signal.signal(signal.SIGTERM, graceful_shutdown)` |
| **Event loop** | `asyncio.run()`, `tokio::main`, `libuv` | `asyncio.run(main())` |
| **Cron-like scheduler** | `schedule.every().day.at(...)`, `cron`, `Timer` | `schedule.every(10).minutes.do(job)` |
| **Watchdog** | `inotify`, `watchdog`, `fsnotify` | `observer.schedule(event_handler, path)` |
| **Health check** | `/health`, `/ready`, `/live` endpoints | `http.HandleFunc("/health", healthHandler)` |
| **Worker pool** | `worker := NewWorker()`, `threadpool` | `pool.submit(process_task)` |

## IPC Entry Points

Inter-Process Communication exposes entry points through named pipes, Unix sockets, shared memory, and message queues.

### IPC Detection Patterns

| IPC Mechanism | Detection | Example |
|---------------|-----------|---------|
| **Unix domain socket** | `socket(AF_UNIX)`, `listen(path)` | `/var/run/app.sock` |
| **Named pipe (FIFO)** | `mkfifo`, `CreateNamedPipe` | `\\.\pipe\app` |
| **D-Bus** | `bus_name`, `interface`, `method` | `org.example.App.Method()` |
| **Shared memory** | `shm_open`, `CreateFileMapping` | Named shared memory region |
| **Signal (POSIX)** | `sigaction`, `signal`, `kill` | Custom user signals (SIGUSR1, SIGUSR2) |
| **Windows messages** | `WndProc`, `RegisterWindowMessage` | Custom window messages |
| **COM/DCOM** | `CoCreateInstance`, `interface GUID` | Out-of-process COM server |
| **Mach ports (macOS)** | `mach_port_allocate`, `bootstrap_check_in` | Service registration |

## Extraction Strategy

### CLI Entry Points
1. Locate main entry file (main.go, main.py, main.rs, cmd/ directory)
2. Find argument parser initialization (argparse, cobra, clap, etc.)
3. Extract all registered commands, subcommands, and flags
4. Trace handler functions to classify:
   - No authentication/authorization → Public
   - Root/admin requirement → Role-Restricted
   - Configuration-only → Admin-level
   - Daemon/server mode → Service entry

### Daemon/Service Entry Points
1. Find main loop and signal registration
2. List all event/callback registrations (timers, watchers, listeners)
3. Identify health check endpoints
4. Check for privilege separation (drop privileges, container boundaries)

### IPC Entry Points
1. Search for socket bind, pipe creation, shared memory allocation
2. Identify message format and handler dispatch
3. Check access control on IPC objects (file permissions, SELinux, AppArmor)

### Classification Guidelines

| Entry Point Type | Typical Access | Notes |
|-----------------|---------------|-------|
| Root CLI commands | Full system access | Often require OS-level permissions |
| Subcommands | Varies | Check each subcommand's restrictions |
| Daemon server mode | Network-accessible | Check network binding (localhost vs 0.0.0.0) |
| Signal handlers | Process owner only | Usually trusted; check for custom signal processing |
| Unix sockets | File permission gated | Check socket file permissions |
| D-Bus methods | Per-method access control | Check policy files (.conf) |
| Scheduled jobs | Timer-triggered | Check who can modify the schedule |
