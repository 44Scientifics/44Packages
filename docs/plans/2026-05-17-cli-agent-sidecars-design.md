# Design Document: CLI Agent Sidecars

**Date**: 2026-05-17
**Topic**: Static manifest and schema sidecars for generated CLIs

## Overview
Extend the OpenAPI CLI generator so it emits compact, machine-readable JSON artifacts alongside the existing Typer command modules. These artifacts are intended for AI agents that need cheap command discovery without paying for verbose CLI help text.

## Goals
- Preserve the current generated CLI entrypoints and runtime behavior.
- Generate a small manifest that lists available commands and their basic input shape.
- Generate one compact schema file per command so agents can fetch details lazily.
- Avoid adding runtime introspection, new services, or dynamic schema generation.

## Proposed Changes

### 1. Static Sidecar Outputs
- Write `manifest.json` into the target output directory.
- Write one schema JSON file per generated command under a dedicated schemas directory.

### 2. Compact Schema Shape
- Capture only input-facing data: command name, HTTP method, path, path/query params, and body shape.
- Normalize OpenAPI types to a small set of primitive names.
- Omit verbose descriptions and response schemas from the default artifacts.

### 3. Generator Ownership
- Keep all sidecar generation inside `OpenAPICLIGenerator.run()` so file emission remains centralized.
- Reuse existing OpenAPI parsing rather than introducing a second parsing layer.

## Verification Plan
- Add tests that assert `run()` creates the manifest and schema files.
- Verify the schema payload contains the expected compact fields for a representative endpoint.
- Run the focused generator test file after implementation.