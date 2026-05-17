# CLI Agent Sidecars Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the OpenAPI CLI generator to emit static manifest and compact per-command schema JSON files for agent-friendly discovery.

**Architecture:** Keep the current Typer code generation unchanged for execution and add a second output stream in `run()` for machine-readable sidecars. Sidecars are derived from the same OpenAPI metadata already used to build command modules, so there is no new runtime dependency or dynamic inspection path.

**Tech Stack:** Python 3.x, pytest, JSON.

---

### Task 1: Add a failing generator test

**Files:**
- Modify: `tests/test_cli_generator.py`
- Modify: `src/FortyFour/Utils/cli_generator.py`

**Step 1: Write the failing test**
- Add a test that runs the generator against a small OpenAPI spec and expects `manifest.json` plus a per-command schema file.

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_cli_generator.py -q`
Expected: FAIL because sidecar files are not yet written.

### Task 2: Emit static sidecar files

**Files:**
- Modify: `src/FortyFour/Utils/cli_generator.py`

**Step 1: Add compact metadata helpers**
- Extract reusable helpers that normalize parameter and body metadata from OpenAPI operations.

**Step 2: Write manifest and schema files in `run()`**
- After command modules are generated, write a small manifest and one schema JSON per command.

**Step 3: Keep runtime stable**
- Do not add new CLI commands or change existing command execution flow.

### Task 3: Verify focused behavior

**Files:**
- Modify: `tests/test_cli_generator.py`
- Modify: `src/FortyFour/Utils/cli_generator.py`

**Step 1: Run the focused test file**
Run: `pytest tests/test_cli_generator.py -q`
Expected: PASS.

**Step 2: Check for broader local regressions if needed**
Run: `pytest tests/test_cli_generator.py tests/test_accounting_module_layout.py -q`
Expected: PASS.