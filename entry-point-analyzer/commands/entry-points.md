---
name: trailofbits:entry-points
description: Identifies state-changing entry points in a codebase (web APIs, CLI, IPC, library exports)
argument-hint: "[directory-path]"
allowed-tools: Read Grep Glob Bash
---

# Analyze Codebase Entry Points

**Arguments:** $ARGUMENTS

Parse the directory path from arguments. If empty, use current directory.

Invoke the `entry-point-analyzer` skill with the directory path for the full workflow.
