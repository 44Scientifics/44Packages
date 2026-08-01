# openapi-to-cli — Design Document

**Date:** 2026-06-28
**Status:** Approved

## Overview

`openapi-to-cli` is a standalone CLI tool that takes an OpenAPI specification (JSON or YAML, from a URL or local file) and generates a complete, ready-to-use Typer-based CLI application.

## Repository Structure

```
openapi-to-cli/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/
    └── openapi_to_cli/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        └── generator.py
```

## CLI Interface

```
openapi-to-cli --spec <url|path> [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--spec` (required) | URL (http/https) or local file path (`.json`, `.yaml`, `.yml`) |
| `--output` | Output directory for generated CLI (default: `./cli-output`) |
| `--base-url` | Override base URL for API calls |
| `--clean / --no-clean` | Clean output directory before generation (default: clean) |
| `--exclude-tag` | Exclude an entire tag from generation. Can be specified multiple times (e.g. `--exclude-tag users --exclude-tag roles`) |
| `--name` | Name for the generated CLI (displayed in help/usage messages). Defaults to the API title from the OpenAPI spec. |
| `--generate-skill` | Enable companion skill generation (default: disabled) |
| `--skill-dir` | Output directory for the companion skill (default: `~/.agents/skills/<cli-name>/`) |

## Generated Output

The tool produces a self-contained Typer CLI project:

```
<output>/
├── main.py              # Entry point — imports and registers all command modules
├── config.py            # BASE_URL and TIMEOUT settings
├── commands/
│   ├── __init__.py
│   ├── companies.py     # One module per OpenAPI tag
│   └── ...
├── schemas/
│   ├── companies__list.json    # Command metadata (params, body, response)
│   └── ...
├── manifest.json        # Index of all generated commands
└── references/
    ├── commands.md      # CLI reference guide
    └── schemas.md       # Data schema field maps
```

## Architecture

### Components

1. **`cli.py`** — Typer app that parses CLI arguments and orchestrates the workflow.
2. **`generator.py`** — Core generation logic (adapted from `FortyFour.Utils.OpenAPICLIGenerator`). Handles spec loading, parsing, and code generation.
3. **`__main__.py`** — Enables `python -m openapi_to_cli`.

### Flow

1. Parse CLI args → determine spec source (URL or file)
2. Load spec (httpx for URLs, file I/O for local, pyyaml for YAML)
3. Initialize generator with spec, config, and output path
4. Generate command modules, schemas, manifest, and references
5. Write main.py entry point
6. Print summary to stdout
7. If `--generate-skill`: copy schemas/, manifest.json, and references/ to skill directory, generate SKILL.md

## Dependencies

### Tool dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI argument parsing |
| `httpx` | Fetch spec from remote URLs |
| `pyyaml` | Parse local YAML specs |
| `rich` | Pretty terminal output |

### Generated CLI dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework |
| `httpx` | HTTP client for API calls |
| `rich` | Pretty-printed responses |

## Key Design Decisions

1. **Separate repo** — The tool lives in its own repository, independent of FortyFour. Cleaner dependency management and distribution.
2. **Typer for the tool** — Using the same framework as the generated output for consistency.
3. **JSON + YAML support** — OpenAPI specs are commonly distributed in both formats. YAML support requires `pyyaml`.
4. **Extracted generator** — The `OpenAPICLIGenerator` class is copied/adapted from FortyFour into `generator.py`, then evolved independently.
5. **Companion skill** — The tool generates an agent skill alongside the CLI, enabling AI assistants to discover and use the generated CLI autonomously. The skill uses the same name as the CLI for discoverability.

## Companion Skill Generation

In addition to generating a Typer CLI project, the tool can also generate (or update) a companion **agent skill** that helps AI agents (like Claude Code) use the generated CLI correctly.

### Skill Output Structure

The skill is written to `--skill-dir` (default: `~/.agents/skills/<cli-name>/`):

```
~/.agents/skills/<cli-name>/
├── SKILL.md               # Agent instructions — how to use this CLI
├── schemas/               # Copy of the generated schemas/
├── manifest.json          # Copy of the generated manifest.json
└── references/            # Copy of the generated references/
```

### SKILL.md Template

The generated `SKILL.md` includes:
- **Frontmatter**: name, description, and trigger keywords for automatic invocation
- **Instructions**: how the agent should use the CLI (commands, flags, patterns)
- **References**: relative paths to `references/commands.md` and `references/schemas.md` for the agent to consult during use

### Update Strategy

When the skill already exists at the target path:
1. **New/Changed files** from the current generation overwrite existing ones (schemas/, manifest.json, references/)
2. **Files not present** in the current generation are left untouched
3. **SKILL.md** is always re-generated with the latest reference content

This means the skill folder is **synced** from the generation output — not wiped and recreated.

### CLI Options

| Argument | Description |
|----------|-------------|
| `--generate-skill` | Enable companion skill generation (default: disabled) |
| `--skill-dir` | Output directory for the skill (default: `~/.agents/skills/<cli-name>/`) |
