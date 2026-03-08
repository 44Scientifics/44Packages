# Design Document: Package Reorganization

**Date**: 2026-03-08
**Topic**: Consolidation and Export Standardization

## Overview
Reorganize the `FortyFour` package to provide a cleaner API for personal scripting. This involves consolidating versioned files, removing redundant modules, and setting up top-level exports in `__init__.py` files.

## Goals
- Simplify import paths (e.g., `from FortyFour.Finance import Company`).
- Remove "Geospace" module (already completed).
- Consolidate `company_v3.py` and `company.py`.
- Expose primary utilities at the sub-package level.

## Proposed Changes

### 1. File System Cleanup
- **Remove**: `src/FortyFour/Finance/company.py` (old version).
- **Rename**: `src/FortyFour/Finance/company_v3.py` to `src/FortyFour/Finance/company.py`.

### 2. Top-Level Exports

#### `src/FortyFour/Finance/__init__.py`
Standardize the API for financial tools:
- `from .company import Company, GAAP`
- `from .utils import get_all_cik, calculate_cagr, get_company_logo_url, create_spark_line`

#### `src/FortyFour/Utils/__init__.py`
Standardize the API for general utilities:
- `from .aws import upload_to_s3, read_file_from_s3`
- `from .helpers import serialize_date_in_dict, remove_nan_values_from_dict`

## Verification Plan
- Create a test script `verify_imports.py` to ensure all intended symbols are importable from their respective sub-packages.
- Ensure existing functionality in `company.py` (formerly v3) remains intact after renaming.
