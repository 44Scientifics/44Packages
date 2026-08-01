# openapi-to-cli Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone CLI tool `openapi-to-cli` that reads an OpenAPI spec (URL or local file, JSON or YAML) and generates a complete Typer-based CLI client with an optional companion agent skill.

**Architecture:** A Python package with `typer` CLI entry point that wraps the `OpenAPICLIGenerator` class (extracted from FortyFour). The generator handles spec loading (httpx for URLs, file I/O + pyyaml for local files), code generation, and optional skill output to `~/.agents/skills/<name>/`.

**Tech Stack:** Python 3.12+, typer, httpx, pyyaml, rich

**Repo location:** New standalone repo — create at `/Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli/`

## Global Constraints

- Python >= 3.12
- Uses `src/` layout (src/openapi_to_cli/)
- Entry point: `openapi-to-cli` via console_scripts in pyproject.toml
- CLI args: --spec (required), --output, --base-url, --clean/--no-clean, --exclude-tag, --name, --generate-skill, --skill-dir
- Skill default path: expanduser("~/.agents/skills/<cli-name>/")
- Support JSON and YAML spec files locally, JSON only via URL
- Generated CLI code must remain unchanged from the original OpenAPICLIGenerator output format

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/openapi_to_cli/__init__.py`
- Create: `src/openapi_to_cli/__main__.py`
- Create: `src/openapi_to_cli/generator.py` (placeholder)
- Create: `src/openapi_to_cli/cli.py` (placeholder)

**Interfaces:**
- Consumes: nothing
- Produces: project skeleton installable via `pip install -e .`

- [ ] **Step 1: Create repo directory and pyproject.toml**

```bash
mkdir -p /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli/src/openapi_to_cli
```

Write `pyproject.toml`:

```toml
[project]
name = "openapi-to-cli"
version = "0.1.0"
description = "Generate a Typer CLI client from any OpenAPI spec"
authors = [
    { name = "44 SCIENTIFICS LTD", email = "44scientifics@gmail.com" }
]
requires-python = ">=3.12"
dependencies = [
    "typer>=0.12.0",
    "httpx>=0.27.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
]

[project.scripts]
openapi-to-cli = "openapi_to_cli.cli:app"

[project.urls]
Homepage = "https://github.com/44Scientifics/openapi-to-cli"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create __init__.py**

```python
from .cli import app
from .generator import OpenAPICLIGenerator

__all__ = ["app", "OpenAPICLIGenerator"]
```

- [ ] **Step 3: Create __main__.py**

```python
from .cli import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Create placeholder generator.py**

```python
# TODO: Implement in Task 2
class OpenAPICLIGenerator:
    pass
```

- [ ] **Step 5: Create placeholder cli.py**

```python
# TODO: Implement in Task 3
import typer

app = typer.Typer()

@app.callback()
def main():
    """Generate a Typer CLI client from any OpenAPI spec."""
    pass
```

- [ ] **Step 6: Verify install**

```bash
cd /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli
pip install -e .
python -c "from openapi_to_cli import OpenAPICLIGenerator; print('OK')"
openapi-to-cli --help
```

Expected: both commands succeed, help text shows.

- [ ] **Step 7: Commit**

```bash
cd /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli
git init
git add -A
git commit -m "chore: scaffold project skeleton"
```

---

### Task 2: Generator Module

**Files:**
- Create: `src/openapi_to_cli/generator.py` (full implementation)
- Create: `tests/test_generator.py`

**Interfaces:**
- Consumes: spec loading helpers (httpx, builtins open, yaml)
- Produces: `OpenAPICLIGenerator` class with:
  - `load_spec(source: str) -> dict`: detects URL vs file, JSON vs YAML, returns parsed spec
  - `run(openapi_url=None, base_url=None, output_dir=None, clean=True, name=None, generate_skill=False, skill_dir=None)`: full generation + optional skill output
  - All existing methods from FortyFour's `cli_generator.py` (`generate_command_code`, `build_command_sidecar`, `build_commands_reference_doc`, etc.)

**Design note:** Copy the full `OpenAPICLIGenerator` class from `/Users/checomart/Dropbox/GitHub/python/libs/44Packages/src/FortyFour/Utils/cli_generator.py`. The class is 812 lines of self-contained logic with no dependencies on other FortyFour modules. Then add:
1. A `load_spec()` method that handles URL vs file and JSON vs YAML detection
2. A `generate_skill()` method that copies schemas/, manifest.json, references/ and writes SKILL.md
3. Update `run()` to accept the new CLI parameters (name, generate_skill, skill_dir)

- [ ] **Step 1: Copy the full OpenAPICLIGenerator from FortyFour**

```bash
cp /Users/checomart/Dropbox/GitHub/python/libs/44Packages/src/FortyFour/Utils/cli_generator.py \
   /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli/src/openapi_to_cli/generator.py
```

- [ ] **Step 2: Add load_spec method to the class (before run())**

Add this method to `OpenAPICLIGenerator`:

```python
def load_spec(self, source: str) -> Dict[str, Any]:
    """Loads an OpenAPI spec from a URL or local file (JSON or YAML)."""
    import yaml

    if source.startswith(("http://", "https://")):
        return self.fetch_openapi(source)

    if not os.path.exists(source):
        raise FileNotFoundError(f"Spec file not found: {source}")

    with open(source, "r", encoding="utf-8") as f:
        content = f.read()

    ext = os.path.splitext(source)[1].lower()
    if ext in (".yaml", ".yml"):
        return yaml.safe_load(content)

    return json.loads(content)
```

- [ ] **Step 3: Update __init__ to accept cli_name and store it properly**

In `__init__`, add a `cli_name` parameter (already exists) and ensure it defaults to `None`:

```python
def __init__(
    self,
    openapi_url: Optional[str] = None,
    base_url: Optional[str] = None,
    excluded_tags: Optional[List[str]] = None,
    commands_dir: str = "commands",
    config_module: Optional[str] = "config",
    cli_name: Optional[str] = None,
):
    self.openapi_url = openapi_url
    self.base_url = base_url
    self.excluded_tags = excluded_tags or ["users", "roles", "profiles", "memberships", "Profiles & Memberships"]
    self.commands_dir = commands_dir
    self.config_module = config_module
    self.cli_name = cli_name
```

- [ ] **Step 4: Add generate_skill method**

Add this method to the class:

```python
def generate_skill(self, target_dir: str, cli_name: str, skill_dir: Optional[str] = None) -> str:
    """Generates or updates a companion agent skill in the skill directory.

    Args:
        target_dir: The generated CLI output directory (has schemas/, manifest.json, references/)
        cli_name: Name of the CLI (used for skill directory name)
        skill_dir: Override path for the skill (default: ~/.agents/skills/<cli-name>/)

    Returns:
        Path to the generated skill directory
    """
    import shutil

    skill_path = skill_dir or os.path.join(os.path.expanduser("~"), ".agents", "skills", cli_name)
    os.makedirs(skill_path, exist_ok=True)

    # Directories/files to sync from generated output
    items_to_sync = ["schemas", "manifest.json", "references"]

    for item in items_to_sync:
        src = os.path.join(target_dir, item)
        dst = os.path.join(skill_path, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        elif os.path.isfile(src):
            shutil.copy2(src, dst)

    # Generate SKILL.md
    skill_md = self._generate_skill_md(cli_name, skill_path)
    with open(os.path.join(skill_path, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md)

    print(f"  Skill generated: {skill_path}")
    return skill_path

def _generate_skill_md(self, cli_name: str, skill_path: str) -> str:
    """Generates the SKILL.md content for the companion skill."""
    from datetime import date

    # Compute relative paths from the skill directory to its resources
    lines = [
        "---",
        f"name: {cli_name}",
        f"description: CLI client for the {cli_name} API, generated from its OpenAPI specification.",
        "---",
        "",
        f"# {cli_name} CLI \u2014 Agent Skill",
        "",
        f"Generated on {date.today().isoformat()} by openapi-to-cli.",
        "",
        "## Usage",
        "",
        f"The `{cli_name}` CLI provides commands to interact with the {cli_name} API.",
        "Use `--help` on any command to see available options.",
        "",
        "## Commands Reference",
        "",
        "See [commands.md](references/commands.md) for the full command reference.",
        "",
        "## Schemas",
        "",
        "See [schemas.md](references/schemas.md) for data schema field maps.",
        "Detailed per-command schema metadata is available in the [schemas/](schemas/) directory.",
        "",
        "## Manifest",
        "",
        "The [manifest.json](manifest.json) file contains a machine-readable index of all commands.",
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 5: Update run() to accept new parameters and use load_spec()**

Replace the existing `run()` method signature and adapt the body:

```python
def run(
    self,
    openapi_url: Optional[str] = None,
    base_url: Optional[str] = None,
    output_dir: Optional[str] = None,
    clean: bool = True,
    spec_source: Optional[str] = None,
    name: Optional[str] = None,
    generate_skill: bool = False,
    skill_dir: Optional[str] = None,
):
    """Executes the generation process."""
    active_openapi = openapi_url or self.openapi_url
    active_base = base_url or self.base_url
    active_name = name or self.cli_name

    # Use spec_source if provided (supports local files), else fallback to openapi_url
    if spec_source:
        print(f"Loading spec from {spec_source}...")
        spec = self.load_spec(spec_source)

        # Infer base_url from spec if not provided
        if not active_base:
            host = spec.get("host", "")
            schemes = spec.get("schemes", ["https"])
            if host:
                active_base = f"{schemes[0]}://{host}"
            print(f"Inferred base_url: {active_base}")

        # Infer name from spec title if not provided
        if not active_name:
            active_name = spec.get("info", {}).get("title", "cli")
            active_name = active_name.lower().replace(" ", "-")
    else:
        if not active_openapi:
            raise ValueError("Either spec_source or openapi_url must be provided")

        # If no base_url, try to infer it from openapi_url
        if not active_base:
            active_base = active_openapi.rsplit("/", 1)[0]
            print(f"Inferred base_url: {active_base}")

        print(f"Fetching OpenAPI spec from {active_openapi}...")
        spec = self.fetch_openapi(active_openapi)

        if not active_name:
            active_name = spec.get("info", {}).get("title", "cli")
            active_name = active_name.lower().replace(" ", "-")

    self.cli_name = active_name
    target_dir = output_dir or os.getcwd()
    if not os.path.isdir(target_dir):
        raise ValueError(f"output_dir does not exist or is not a directory: {target_dir}")

    # ... rest of existing run() logic unchanged from original (lines 660-810 of cli_generator.py)
```

**Important:** Keep the rest of `run()` exactly as it was (the generation logic after spec loading — creating dirs, iterating paths/tags, writing modules, manifest, references). Just ensure that:
1. `self.cli_name` is set before the generation code runs
2. At the very end of the method (after writing main.py, before the final print), add:

```python
        # Generate companion skill if requested
        if generate_skill:
            self.generate_skill(
                target_dir=target_dir,
                cli_name=active_name,
                skill_dir=skill_dir,
            )
```

This ensures the skill is created after all files are written.

- [ ] **Step 6: Write tests for load_spec**

```python
import pytest
import json
import yaml
import tempfile
import os
from openapi_to_cli.generator import OpenAPICLIGenerator

def test_load_spec_from_file_json():
    """load_spec should parse a local JSON file."""
    spec_data = {"openapi": "3.0.0", "info": {"title": "Test API"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec_data, f)
        f.flush()
        gen = OpenAPICLIGenerator()
        result = gen.load_spec(f.name)
        assert result == spec_data
        os.unlink(f.name)


def test_load_spec_from_file_yaml():
    """load_spec should parse a local YAML file."""
    spec_data = {"openapi": "3.0.0", "info": {"title": "Test API"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(spec_data, f)
        f.flush()
        gen = OpenAPICLIGenerator()
        result = gen.load_spec(f.name)
        assert result == spec_data
        os.unlink(f.name)


def test_load_spec_file_not_found():
    """load_spec should raise FileNotFoundError for missing files."""
    gen = OpenAPICLIGenerator()
    with pytest.raises(FileNotFoundError):
        gen.load_spec("/nonexistent/spec.json")
```

- [ ] **Step 7: Run tests**

```bash
cd /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli
mkdir -p tests
# Write the test file from Step 6 to tests/test_generator.py
pip install pytest
pytest tests/test_generator.py -v
```

Expected: 3 tests pass (1 for JSON, 1 for YAML, 1 for FileNotFoundError).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: implement generator with spec loading and skill generation"
```

---

### Task 3: CLI Entry Point

**Files:**
- Create: `src/openapi_to_cli/cli.py` (full implementation)
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `OpenAPICLIGenerator` from `generator.py`
- Produces: `app` Typer instance registered as `openapi-to-cli` console_scripts entry point

- [ ] **Step 1: Write the failing CLI test**

Write `tests/test_cli.py`:

```python
import pytest
from typer.testing import CliRunner
from openapi_to_cli.cli import app

runner = CliRunner()


def test_cli_help():
    """CLI should print help with --help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Generate a Typer CLI client" in result.stdout


def test_cli_missing_spec():
    """CLI should error when --spec is missing."""
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert "Missing option" in result.stdout or "Error" in result.stdout
```

Run:

```bash
cd /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli
pytest tests/test_cli.py -v
```

Expected: FAIL — cli.py is still a placeholder.

- [ ] **Step 2: Implement full cli.py**

Write `src/openapi_to_cli/cli.py`:

```python
import typer
from typing import Optional, List
from pathlib import Path
from .generator import OpenAPICLIGenerator

app = typer.Typer(
    name="openapi-to-cli",
    help="Generate a Typer CLI client from any OpenAPI specification.",
)


@app.callback()
def main():
    """Generate a Typer CLI client from any OpenAPI specification."""
    pass


@app.command()
def generate(
    spec: str = typer.Argument(
        ...,
        help="OpenAPI spec: URL (http/https) or path to local .json/.yaml/.yml file",
    ),
    output: Optional[Path] = typer.Option(
        "./cli-output",
        help="Output directory for the generated CLI",
        file_okay=False,
        dir_okay=True,
    ),
    base_url: Optional[str] = typer.Option(
        None,
        help="Override the base URL for API calls (default: inferred from spec)",
    ),
    clean: bool = typer.Option(
        True,
        help="Clean output directory before generating",
    ),
    exclude_tag: Optional[List[str]] = typer.Option(
        None,
        help="Exclude an OpenAPI tag from generation (can be repeated)",
    ),
    name: Optional[str] = typer.Option(
        None,
        help="Name for the generated CLI (default: API title from spec)",
    ),
    generate_skill: bool = typer.Option(
        False,
        help="Generate a companion agent skill in ~/.agents/skills/<name>/",
    ),
    skill_dir: Optional[Path] = typer.Option(
        None,
        help="Output directory for the companion skill (default: ~/.agents/skills/<name>/)",
        file_okay=False,
        dir_okay=True,
    ),
):
    """Generate a CLI client from an OpenAPI specification."""
    # Determine if spec is a URL or local file
    is_url = spec.startswith(("http://", "https://"))
    is_local = Path(spec).exists()

    if not is_url and not is_local:
        typer.echo(f"Error: spec '{spec}' is not a valid URL or existing file", err=True)
        raise typer.Exit(code=1)

    generator = OpenAPICLIGenerator(
        excluded_tags=exclude_tag,
        cli_name=name,
    )

    output_dir = str(output.resolve()) if output else os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    resolved_skill_dir = str(skill_dir.resolve()) if skill_dir else None

    try:
        if is_url:
            generator.run(
                openapi_url=spec,
                base_url=base_url,
                output_dir=output_dir,
                clean=clean,
                name=name,
                generate_skill=generate_skill,
                skill_dir=resolved_skill_dir,
            )
        else:
            generator.run(
                spec_source=spec,
                base_url=base_url,
                output_dir=output_dir,
                clean=clean,
                name=name,
                generate_skill=generate_skill,
                skill_dir=resolved_skill_dir,
            )

        typer.echo(f"\n\u2705 CLI generated successfully in: {output_dir}")
        if generate_skill:
            skill_path = resolved_skill_dir or os.path.join(
                os.path.expanduser("~"), ".agents", "skills", generator.cli_name or name or "cli"
            )
            typer.echo(f"   Companion skill: {skill_path}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
```

**Note:** Add `import os` at the top of the file.

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli
pytest tests/test_cli.py -v
```

Expected: 2 tests pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: implement CLI entry point with all options"
```

---

### Task 4: Integration — End-to-End Smoke Test

**Files:**
- Create: `tests/test_integration.py` (or just run manually)
- Modify: none

- [ ] **Step 1: Create a minimal OpenAPI spec for testing**

Write `/tmp/test-api-spec.json`:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Pet Store API",
    "version": "1.0.0"
  },
  "servers": [{"url": "https://api.petstore.example.com"}],
  "paths": {
    "/pets": {
      "get": {
        "tags": ["pets"],
        "summary": "List all pets",
        "operationId": "get_all_pets",
        "responses": {
          "200": {
            "description": "A list of pets",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Pet"
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": ["pets"],
        "summary": "Create a pet",
        "operationId": "create_pets",
        "responses": {
          "201": {
            "description": "Created"
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Pet": {
        "type": "object",
        "properties": {
          "id": {"type": "integer"},
          "name": {"type": "string"},
          "tag": {"type": "string"}
        }
      }
    }
  }
}
```

- [ ] **Step 2: Run openapi-to-cli with the test spec (no skill)**

```bash
cd /tmp
rm -rf /tmp/test-cli-output
openapi-to-cli /tmp/test-api-spec.json --output /tmp/test-cli-output --name petstore
```

Expected: 
- `/tmp/test-cli-output/main.py` exists
- `/tmp/test-cli-output/commands/pets.py` exists
- `/tmp/test-cli-output/manifest.json` exists

- [ ] **Step 3: Verify the generated CLI works**

```bash
cd /tmp/test-cli-output
python main.py --help
python main.py pets --help
python main.py pets list
```

Expected: help text shows, list command runs and hits the API (may fail with network error — that's OK, it means the code compiles and runs).

- [ ] **Step 4: Run openapi-to-cli with skill generation**

```bash
rm -rf /tmp/test-cli-output /tmp/test-skill
openapi-to-cli /tmp/test-api-spec.json \
  --output /tmp/test-cli-output \
  --name petstore \
  --generate-skill \
  --skill-dir /tmp/test-skill
```

Expected:
- `/tmp/test-skill/SKILL.md` exists with frontmatter and usage instructions
- `/tmp/test-skill/schemas/` directory exists with schema files
- `/tmp/test-skill/manifest.json` exists
- `/tmp/test-skill/references/` directory exists

- [ ] **Step 5: Verify skill update preserves extra files**

```bash
# Add a custom file to the skill
echo "extra" > /tmp/test-skill/extra-file.txt

# Re-run generation (should sync but keep extra-file.txt)
openapi-to-cli /tmp/test-api-spec.json \
  --output /tmp/test-cli-output \
  --name petstore \
  --generate-skill \
  --skill-dir /tmp/test-skill

# Verify extra file still exists
cat /tmp/test-skill/extra-file.txt
```

Expected: `extra-file.txt` still exists (files not in generation output are preserved).

- [ ] **Step 6: Commit**

```bash
cd /Users/checomart/Dropbox/GitHub/python/libs/openapi-to-cli
git add -A
git commit -m "test: add integration smoke tests"
```

---

### Task 5: Finalize — README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# openapi-to-cli

Generate a complete Typer-based CLI client from any OpenAPI specification.

## Installation

```bash
pip install openapi-to-cli
```

## Usage

```bash
# From an OpenAPI JSON URL
openapi-to-cli https://api.example.com/openapi.json --output ./my-cli

# From a local JSON file
openapi-to-cli ./spec.json --output ./my-cli

# From a local YAML file
openapi-to-cli ./spec.yaml --output ./my-cli

# Specify a name for the generated CLI
openapi-to-cli ./spec.json --name myapi --output ./my-cli

# Generate a companion agent skill
openapi-to-cli ./spec.json --name myapi --output ./my-cli --generate-skill
```

## Options

| Option | Description |
|--------|-------------|
| `spec` (required) | URL or local path to OpenAPI spec (.json, .yaml, .yml) |
| `--output` | Output directory (default: ./cli-output) |
| `--base-url` | Override API base URL |
| `--clean / --no-clean` | Clean output before generation (default: clean) |
| `--exclude-tag` | Exclude a tag (can be repeated) |
| `--name` | Name for the generated CLI (default: API title) |
| `--generate-skill` | Generate companion agent skill |
| `--skill-dir` | Output directory for the skill (default: ~/.agents/skills/<name>/) |

## Generated Output

```
./cli-output/
├── main.py              # CLI entry point
├── config.py            # Base URL and timeout
├── commands/            # One module per OpenAPI tag
├── schemas/             # Per-command metadata
├── manifest.json        # Command index
└── references/          # Command and schema documentation
```

## Companion Skill

With `--generate-skill`, the tool creates an agent skill at `~/.agents/skills/<name>/`:

```
~/.agents/skills/<name>/
├── SKILL.md             # Agent instructions
├── schemas/             # Command metadata
├── manifest.json        # Command index
└── references/          # Documentation
```

Skills are synced — existing files are updated, but files not in the current generation are preserved.

## Development

```bash
git clone https://github.com/44Scientifics/openapi-to-cli
cd openapi-to-cli
pip install -e .
```

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "docs: add README with usage examples"
```
