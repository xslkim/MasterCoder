# MasterCoder User Guide

## Overview

MasterCoder is a terminal-first AI coding assistant intended for local development workflows. In the current release branch, the shipped user-facing surface is the `mastercoder` CLI under `src/mastercoder/`.

This guide documents the capabilities that are actually wired into the startup path of the current release. The repository also contains internal automation code used to build the product, but that automation framework is not required for normal end-user usage.

## What This Release Supports

- Interactive CLI startup through `mastercoder`
- Non-interactive stdin mode such as `echo "..." | mastercoder`
- Command-line overrides for model, API key, API base URL, color output, and auto-approve mode
- Global config and project config loading
- `MASTERCODER.md` project instruction injection
- Git repository detection, branch display in the prompt, and Git summary injection into the model context
- `@file` references that inline file contents into the user message before the request is sent

## What Is Not Fully Wired Yet

- `--resume` is parsed by the CLI, but the startup path does not yet resume a stored session automatically
- The repository contains session persistence modules, but the top-level CLI does not expose a user command for browsing or switching sessions
- The fallback mode without an API key is a basic local REPL, not an offline assistant
- The banner still mentions `/help`, but the current interactive AI path does not wire a slash-command dispatcher into startup

## Installation

### Requirements

- Linux, macOS, or another Unix-like shell environment
- Python 3.10 or later
- Network access to an OpenAI-compatible chat completion endpoint

### Install From Source

```bash
git clone git@github.com:xslkim/MasterCoder.git
cd MasterCoder
python3 -m pip install -e .
```

This installs the `mastercoder` console script defined in `pyproject.toml`.

## Configuration

MasterCoder merges configuration from several sources.

Precedence order:

1. Command-line flags
2. Environment variables
3. Project config file
4. Global config file
5. Built-in defaults

### Global Config File

Path:

```text
~/.mastercoder/config.json
```

Example:

```json
{
  "api_key": "YOUR_API_KEY",
  "api_base_url": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "max_tokens": 4096,
  "temperature": 0.0,
  "auto_approve": false,
  "system_prompt": ""
}
```

### Project Config File

Path:

```text
<project>/.mastercoder/config.json
```

Use this when a specific repository should override your global defaults.

### Environment Variables

Supported environment variables:

- `MASTERCODER_API_KEY`
- `MASTERCODER_API_BASE_URL`
- `MASTERCODER_MODEL`

Example:

```bash
export MASTERCODER_API_KEY="YOUR_API_KEY"
export MASTERCODER_API_BASE_URL="https://api.openai.com/v1"
export MASTERCODER_MODEL="gpt-4o"
```

## Command-Line Reference

| Flag | Short | Meaning |
| --- | --- | --- |
| `--model NAME` | `-m` | Override the configured model |
| `--api-key KEY` | none | Override API key |
| `--api-url URL` | none | Override API base URL |
| `--auto-approve` | `-y` | Enable auto-approve mode |
| `--resume [SESSION_ID]` | `-r` | Parsed by CLI, but not yet connected to startup resume |
| `--version` | `-v` | Print `MasterCoder v0.1.0` and exit |
| `--no-color` | none | Disable ANSI color output |
| `--help` | `-h` | Print help and exit |

Security note:

`--api-key` is visible in process arguments. Prefer `MASTERCODER_API_KEY` or a config file for normal usage.

## Starting Interactive Mode

The normal path is:

```bash
mastercoder
```

With explicit overrides:

```bash
mastercoder -m deepseek-chat --no-color
mastercoder --api-url https://example.com/v1
mastercoder --api-key "$MASTERCODER_API_KEY"
```

### Prompt Format

Inside a Git repository, the prompt includes the current branch and refreshes it each time input is requested.

Typical format:

```text
mastercoder [gpt-4o] ~/project (main) >
```

Outside a Git repository, the branch segment is omitted.

## Non-Interactive Mode

When stdin is not a TTY, MasterCoder switches to one-shot mode.

Example:

```bash
echo "Summarize the current repository structure" | mastercoder
```

Behavior:

- Reads the full stdin payload
- Sends one request to the configured model
- Prints plain text output
- Exits with code `0` on success
- Forces `auto_approve = true` unless you already overrode it

If no API key is configured in non-interactive mode, the command prints an error and exits with code `1`.

## Project Instructions With MASTERCODER.md

If a file named `MASTERCODER.md` exists in the current working directory, its content is injected into the system prompt.

Path:

```text
<project>/MASTERCODER.md
```

Use this file for repository-specific instructions such as:

- Preferred coding style
- Build or test commands
- Architectural constraints
- Language or framework conventions

Notes:

- Files larger than 50 KB are truncated to the first 50 KB
- Truncation is UTF-8 safe
- The effective prompt order is built-in prompt, then `MASTERCODER.md`, then Git info, then custom `system_prompt`

## Git-Aware Context

When MasterCoder starts inside a Git repository, it collects a lightweight summary once and appends it to the system prompt.

Collected information:

- Current branch
- Up to 5 recent commits from `git log --oneline -5`
- Up to 20 lines from `git status --short`

Git behavior details:

- Each Git command uses a 2-second timeout
- Failures are ignored silently
- If the working tree is clean, the injected status section becomes `Status: clean`

This helps the assistant understand current branch context and uncommitted file changes.

## `@file` Context Injection

Interactive input supports file references prefixed with `@`.

Examples:

```text
Explain @src/mastercoder/main.py
Review @"docs/product spec.md"
Compare @src/mastercoder/config.py and @tests/test_config.py
```

Behavior:

- Relative paths are resolved against the current working directory
- Up to 10 file references are accepted per message
- Directories are rejected
- Binary files are rejected
- Files larger than 1 MB are rejected
- Paths are checked against the sandbox rules before reading
- The original `@file` syntax is removed from the text sent to the model and replaced with file content blocks

Tab completion is installed for interactive `@file` references when `readline` is available.

## Known Runtime Behavior Without API Key

If you start `mastercoder` interactively without a configured API key, the startup path falls back to a basic local REPL that:

- prints the startup banner
- echoes typed input
- supports `/exit`

This is a compatibility fallback only. To use the AI assistant, configure an API key.

## Practical Examples

### Use a Temporary Model Override

```bash
mastercoder -m deepseek-chat
```

### Use Project-Specific Instructions

```bash
cat > MASTERCODER.md <<'EOF'
Always preserve the public API.
Run pytest before suggesting code changes.
EOF

mastercoder
```

### Ask About a Specific File

```text
Please explain @src/mastercoder/conversation.py and highlight error-handling behavior.
```

### Send One Shot Through a Pipe

```bash
printf 'Summarize the current branch and changed files.' | mastercoder
```

## Troubleshooting

### `Error: API key not configured`

Set one of the following:

- `MASTERCODER_API_KEY`
- `~/.mastercoder/config.json` with `api_key`
- project `.mastercoder/config.json` with `api_key`
- `--api-key` on the command line

### Git branch is missing from the prompt

Possible reasons:

- current directory is not inside a Git repository
- `git` is unavailable in `PATH`
- Git command timed out or failed

### `@file` reference does not expand

Possible reasons:

- path points to a directory
- file is outside the sandbox
- file is larger than 1 MB
- file is binary or unreadable
- more than 10 references were provided in a single message

### No color output when expected

Possible reasons:

- stdout is not a TTY
- you started with `--no-color`

## Release Scope Reminder

This guide describes the shipped product CLI on the `release/v0.1.0` branch. The repository also contains automation code under `src/mastercoder_automation/`; that framework is used for development workflow orchestration and is not required for normal end-user operation of `mastercoder`.