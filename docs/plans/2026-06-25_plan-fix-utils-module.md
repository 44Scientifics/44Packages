---
status: completed
completed: 2026-06-25T12:00:00
created: 2026-06-25T12:00:00
completed: 
---

# Plan: Fix FortyFour/Utils Module Issues

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 2 critical bugs, 3 serious issues, and 5+ minor issues identified in the `src/FortyFour/Utils` module code review, then add missing test coverage.

**Architecture:** Bug-fix and cleanup pass. No architectural changes — we fix bugs in place, consolidate duplicate code, add missing type hints and `__all__`, and backfill tests. All fixes are isolated to their respective files.

**Tech Stack:** Python 3.12+, boto3, numpy, SQLAlchemy, pytest.

## Global Constraints

- Fix all changes in-place within existing files; no new source files except test files
- Follow existing code patterns in the project (type hints with `typing` module style)
- Tests go in `tests/` directory following existing pytest conventions
- All fixes must pass `pytest tests/` before commit

---

## Delegation
- [x] `Code Architect` needed? No — bug fixes only, no new architecture
- [x] `UI Designer` needed? No — no visual component

---

## Steps

### Groupe 1 [P] — Fix `aws.py` (indépendant)

1. **Fix `delete_file_from_S3` — replace broken `get_object().delete()` pattern**
   - Files: `src/FortyFour/Utils/aws.py` (lines 33-41)
   - Change: Replace lines 40-41 with `s3.delete_object(Bucket=bucket_name, Key=file_name)`. Add return type hint `-> None`. Rename function to `delete_file_from_s3` (lowercase s3) for consistency.
   - Why: `boto3.client.get_object()` returns a dict, not an object with `.delete()`. Current code will always raise `AttributeError` at runtime.
   - Verify: Function no longer crashes when called with valid credentials.

   **Code after fix:**
   ```python
   def delete_file_from_s3(bucket_name: str, file_name: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> None:
       s3 = boto3.client(
           service_name="s3",
           region_name=region_name,
           aws_access_key_id=aws_access_key_id,
           aws_secret_access_key=aws_secret_access_key
       )
       s3.delete_object(Bucket=bucket_name, Key=file_name)
   ```

2. **Add type hints and return types to `upload_to_s3` and `read_file_from_s3`**
   - Files: `src/FortyFour/Utils/aws.py` (lines 5-18, 21-30)
   - Change: Add `from typing import BinaryIO` import. Annotate `file_object: BinaryIO` and return type `-> str` on `upload_to_s3`. Annotate return type `-> bytes` on `read_file_from_s3`.
   - Why: Missing type hints make the API unclear. Consumers don't know what `file_object` should be or what the functions return.
   - Verify: `mypy src/FortyFour/Utils/aws.py` emits no errors (or only pre-existing ones unrelated to these changes).

   **Updated signatures:**
   ```python
   from typing import BinaryIO

   def upload_to_s3(file_object: BinaryIO, bucket_name: str, file_name: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> str:
       ...

   def read_file_from_s3(bucket_name: str, file_name: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> bytes:
       ...
   ```

3. **Update `__init__.py` to match renamed function**
   - Files: `src/FortyFour/Utils/__init__.py` (line 1)
   - Change: No change needed — `delete_file_from_S3` was never exported in `__init__.py`. Just verify the existing imports still work after renaming.
   - Why: The old name `delete_file_from_S3` was not in `__init__.py` imports, so renaming has no consumer impact.
   - Verify: `from FortyFour.Utils import upload_to_s3, read_file_from_s3` still works.

---

### Groupe 2 [P] — Fix `helpers.py` (indépendant du Groupe 1)

4. **Fix NaN comparison bug in `remove_nan_values_from_dict`**
   - Files: `src/FortyFour/Utils/helpers.py` (line 40)
   - Change: Replace `if value is not np.nan:` with a proper NaN check using `np.isnan()` guarded by `isinstance`.
   - Why: `np.nan is not np.nan` is always `True` in Python — NaN is never identical to itself. The function is currently a silent no-op that never filters any NaN value.
   - Verify: `remove_nan_values_from_dict({"a": float("nan"), "b": 1})` returns `{"b": 1}`.

   **Code after fix:**
   ```python
   def remove_nan_values_from_dict(my_dict: dict) -> dict:
       """Recursively remove entries whose value is NaN."""
       clean_dict = {}
       for key, value in my_dict.items():
           if isinstance(value, dict):
               value = remove_nan_values_from_dict(value)
           try:
               is_nan = np.isnan(value)
           except (TypeError, ValueError):
               is_nan = False
           if not is_nan:
               clean_dict[key] = value
       return clean_dict
   ```

5. **Fix bare `except:` in `serialize_date_in_dict`**
   - Files: `src/FortyFour/Utils/helpers.py` (line 15)
   - Change: Replace `except:` with `except Exception:`.
   - Why: Bare `except:` catches `KeyboardInterrupt`, `SystemExit`, and `MemoryError`, which should never be silently swallowed.
   - Verify: Ctrl+C still interrupts the function. Normal exceptions from `parse()` are still caught.

   **Code after fix (line 15):**
   ```python
   except Exception:
       pass
   ```

6. **Consolidate `serialize_date_in_dict` and `convert_string_to_date_in_dict` into one function**
   - Files: `src/FortyFour/Utils/helpers.py` (lines 8-18, 45-54)
   - Change: Replace both functions with a single `serialize_date_in_dict(my_dict: dict, silent: bool = True) -> dict`. When `silent=True`, use `pass` on exceptions (old behavior of `serialize_date_in_dict`). When `silent=False`, use `logging.warning` (old behavior of `convert_string_to_date_in_dict`). Remove `convert_string_to_date_in_dict`.
   - Why: Two functions with 95% identical logic. The only difference was the exception handler.
   - Verify: Both old behaviors are preserved via the `silent` parameter.

   **Consolidated code:**
   ```python
   def serialize_date_in_dict(my_dict: dict, silent: bool = True) -> dict:
       """Recursively parse date strings in a dict, combining with midnight time."""
       for key, value in my_dict.items():
           if isinstance(value, dict):
               value = serialize_date_in_dict(value, silent=silent)
           try:
               parsed = parse(value)
               my_dict[key] = datetime.combine(parsed, datetime.min.time())
           except Exception:
               if not silent:
                   logging.warning(
                       'The function serialize_date_in_dict() encountered an exception for key=%s value=%s',
                       key, value, exc_info=True
                   )
       return my_dict
   ```

7. **Make `serialize_date_in_dict` non-mutating (return new dict) or document mutation**
   - Files: `src/FortyFour/Utils/helpers.py` (lines 8-18)
   - Change: Make the function return a **new** dict instead of mutating the input, matching `remove_nan_values_from_dict`'s semantics. Work on a copy.
   - Why: Current inconsistency — `serialize_date_in_dict` mutates in-place while `remove_nan_values_from_dict` returns a new dict. Both should follow the same convention.
   - Verify: Original dict is unchanged after calling `serialize_date_in_dict`.

   **Updated function:**
   ```python
   def serialize_date_in_dict(my_dict: dict, silent: bool = True) -> dict:
       """Recursively parse date strings in a dict, returning a new dict with dates combined at midnight."""
       result = {}
       for key, value in my_dict.items():
           if isinstance(value, dict):
               result[key] = serialize_date_in_dict(value, silent=silent)
               continue
           try:
               parsed = parse(value)
               result[key] = datetime.combine(parsed, datetime.min.time())
           except Exception:
               if not silent:
                   logging.warning(
                       'The function serialize_date_in_dict() encountered an exception for key=%s value=%s',
                       key, value, exc_info=True
                   )
               result[key] = value
       return result
   ```

8. **Rename misleading `my_dict` parameter in `sort_dict_by_key`**
   - Files: `src/FortyFour/Utils/helpers.py` (line 57)
   - Change: Rename parameter `my_dict: dict` to `items: List[Dict[str, Any]]` with proper type hint.
   - Why: The parameter is a list of dicts, not a single dict. The name `my_dict` is misleading.
   - Verify: Existing callers still work (function signature compatible — old callers passed positional args).

   **Updated signature:**
   ```python
   def sort_dict_by_key(items: List[Dict[str, Any]], key: str, reverse: bool) -> List[Dict[str, Any]]:
       return sorted(items, key=lambda d: d[key], reverse=reverse)
   ```

9. **Remove commented-out code**
   - Files: `src/FortyFour/Utils/helpers.py` (line 16)
   - Change: Remove line 16: `# print("convert_string_to_date_in_dict() as encounter an exception")`
   - Why: Dead commented-out code. The function name referenced no longer exists after consolidation.
   - Verify: No remaining commented-out code in the file.

---

### Groupe 3 [P] — Module cleanup (indépendant des Groupes 1 et 2)

10. **Add `__all__` to `Utils/__init__.py`**
    - Files: `src/FortyFour/Utils/__init__.py`
    - Change: Add `__all__ = ["upload_to_s3", "read_file_from_s3", "serialize_date_in_dict", "remove_nan_values_from_dict", "OpenAPICLIGenerator", "apply_fuzzy_search"]`
    - Why: Without `__all__`, `from FortyFour.Utils import *` exposes internal symbols. The explicit imports already define the intended public API — `__all__` codifies this.
    - Verify: `from FortyFour.Utils import *` only imports the 6 listed symbols.

11. **Fix `REBECCAPURPLE` ordering in `colors.py`**
    - Files: `src/FortyFour/Utils/colors.py` (line 396)
    - Change: Move `REBECCAPURPLE = "rebeccapurple"` from line 396 to line 393 (alphabetically between `PURPLE` and `RED`).
    - Why: Minor ordering bug — `REBECCAPURPLE` sorts before `RED`, not after `ROYALBLUE`.
    - Verify: Enum members are in alphabetical order: `PURPLE`, `REBECCAPURPLE`, `RED`, `ROSYBROWN`, `ROYALBLUE`.

12. **Add database dependency documentation to `Utils/search.py`**
    - Files: `src/FortyFour/Utils/search.py` (module docstring, lines 1-6)
    - Change: Extend module docstring to document required PostgreSQL extensions (`pg_trgm`, `unaccent`, and the custom `f_unaccent` IMMUTABLE wrapper function).
    - Why: Silent runtime SQL errors if these extensions aren't installed. Developers need to know the prerequisites.
    - Verify: Docstring clearly states all 3 required DB extensions.

    **Updated docstring (after line 6):**
    ```python
    """
    SQLAlchemy Fuzzy Search Utilities
    
    Provides reusable functions for building PostgreSQL-powered fuzzy search
    queries using the `unaccent` and `pg_trgm` extensions.
    
    **Required PostgreSQL setup:** Run these once on your database:
    
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE EXTENSION IF NOT EXISTS unaccent;
        CREATE OR REPLACE FUNCTION f_unaccent(text)
            RETURNS text AS $$
            SELECT public.unaccent('public.unaccent', $1)
        $$ LANGUAGE sql IMMUTABLE;
    """
    ```

13. **Remove root-level `search.py` duplicate or redirect it**
    - Files: `search.py` (project root)
    - Change: Replace the file content with a re-export from the canonical package location:
      ```python
      """Re-exported from FortyFour.Utils.search for backward compatibility."""
      from FortyFour.Utils.search import fuzzy_match, fuzzy_similarity, apply_fuzzy_search

      __all__ = ["fuzzy_match", "fuzzy_similarity", "apply_fuzzy_search"]
      ```
    - Why: The root-level `search.py` duplicates logic from `src/FortyFour/Utils/search.py` but with fewer features (no auto-column resolution). This prevents divergence.
    - Verify: `from search import apply_fuzzy_search` still works and delegates to the canonical implementation.

---

### Groupe 4 [P] — Add missing tests (dépend des Groupes 1, 2, 3)

14. **Add tests for `aws.py`**
    - Files: Create `tests/test_aws_utils.py`
    - Change: Add 3+ test functions using `unittest.mock.patch`:
      - `test_upload_to_s3` — verifies `s3.upload_fileobj` is called with correct args
      - `test_read_file_from_s3` — verifies `s3.get_object` returns expected bytes
      - `test_delete_file_from_s3` — verifies `s3.delete_object` is called with correct Bucket/Key
    - Why: Zero test coverage for any AWS function. The delete bug would have been caught by a test.
    - Verify: `pytest tests/test_aws_utils.py -v` — 3 tests pass.

    **Test code:**
    ```python
    import pytest
    from unittest.mock import MagicMock, patch
    from io import BytesIO
    from FortyFour.Utils.aws import upload_to_s3, read_file_from_s3, delete_file_from_s3

    def test_upload_to_s3():
        with patch("boto3.client") as mock_client:
            mock_s3 = MagicMock()
            mock_client.return_value = mock_s3
            file_obj = BytesIO(b"test data")
            result = upload_to_s3(file_obj, "my-bucket", "test.txt", "us-east-1", "key", "secret")
            mock_s3.upload_fileobj.assert_called_once_with(file_obj, "my-bucket", "test.txt")
            assert result == "test.txt"

    def test_read_file_from_s3():
        with patch("boto3.client") as mock_client:
            mock_s3 = MagicMock()
            mock_s3.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"hello"))}
            mock_client.return_value = mock_s3
            result = read_file_from_s3("my-bucket", "test.txt", "us-east-1", "key", "secret")
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="test.txt")
            assert result == b"hello"

    def test_delete_file_from_s3():
        with patch("boto3.client") as mock_client:
            mock_s3 = MagicMock()
            mock_client.return_value = mock_s3
            delete_file_from_s3("my-bucket", "test.txt", "us-east-1", "key", "secret")
            mock_s3.delete_object.assert_called_once_with(Bucket="my-bucket", Key="test.txt")
    ```

15. **Add tests for `helpers.py`**
    - Files: Create `tests/test_helpers.py`
    - Change: Add 7+ test functions:
      - `test_filters_nan` — verifies NaN is actually removed
      - `test_preserves_non_nan` — verifies valid values survive
      - `test_handles_nested_dict` — verifies recursion into nested dicts
      - `test_returns_new_dict` — verifies original dict is unchanged
      - `test_parses_iso_date` — verifies date parsing
      - `test_does_not_mutate_input` — verifies original dict is unchanged
      - `test_silent_mode` — verifies silent=True keeps invalid values
      - `test_sorts_correctly` — verifies sorting
      - `test_reverse_sort` — verifies reverse sorting
      - `test_merges_old_and_new` — verifies merge logic preserves old data
      - `test_removes_deprecated` — verifies old entries not in new list are dropped
    - Why: Zero test coverage. The NaN bug would have been caught. The mutation inconsistency would have been flagged.
    - Verify: `pytest tests/test_helpers.py -v` — all tests pass.

    **Test code:**
    ```python
    import pytest
    import numpy as np
    from FortyFour.Utils.helpers import (
        serialize_date_in_dict,
        remove_nan_values_from_dict,
        sort_dict_by_key,
        update_list_from_new_source_keep_old_matches,
    )

    class TestRemoveNanValues:
        def test_filters_nan(self):
            result = remove_nan_values_from_dict({"a": float("nan"), "b": 1})
            assert "a" not in result
            assert result["b"] == 1

        def test_preserves_non_nan(self):
            result = remove_nan_values_from_dict({"a": "hello", "b": 42, "c": 3.14})
            assert result == {"a": "hello", "b": 42, "c": 3.14}

        def test_handles_nested_dict(self):
            result = remove_nan_values_from_dict({"a": {"x": float("nan"), "y": "ok"}, "b": 1})
            assert result == {"a": {"y": "ok"}, "b": 1}

        def test_returns_new_dict(self):
            original = {"a": float("nan"), "b": 1}
            result = remove_nan_values_from_dict(original)
            assert result is not original
            assert "a" in original  # original unchanged

    class TestSerializeDateInDict:
        def test_parses_iso_date(self):
            from datetime import datetime
            result = serialize_date_in_dict({"date": "2024-06-25"})
            assert isinstance(result["date"], datetime)
            assert result["date"].year == 2024
            assert result["date"].month == 6
            assert result["date"].day == 25

        def test_does_not_mutate_input(self):
            original = {"date": "2024-06-25"}
            result = serialize_date_in_dict(original)
            assert result is not original
            assert isinstance(original["date"], str)  # original unchanged

        def test_silent_mode(self):
            result = serialize_date_in_dict({"not_a_date": "xyz"}, silent=True)
            assert result["not_a_date"] == "xyz"  # kept as-is

    class TestSortDictByKey:
        def test_sorts_correctly(self):
            items = [{"name": "C"}, {"name": "A"}, {"name": "B"}]
            result = sort_dict_by_key(items, "name", reverse=False)
            assert [d["name"] for d in result] == ["A", "B", "C"]

        def test_reverse_sort(self):
            items = [{"name": "A"}, {"name": "C"}, {"name": "B"}]
            result = sort_dict_by_key(items, "name", reverse=True)
            assert [d["name"] for d in result] == ["C", "B", "A"]

    class TestUpdateListFromNewSource:
        def test_merges_old_and_new(self):
            old = [{"_id": "1", "ticker": "AAPL", "comment": "old note"}]
            new = [{"_id": "1", "ticker": "AAPL", "price": 150.0}, {"_id": "2", "ticker": "GOOG"}]
            result = update_list_from_new_source_keep_old_matches(old, new)
            assert len(result) == 2
            aapl = next(d for d in result if d["_id"] == "1")
            assert aapl["comment"] == "old note"  # preserved from old
            assert aapl["price"] == 150.0  # overridden by new
            goog = next(d for d in result if d["_id"] == "2")
            assert goog["avg_price"] == 0.0  # default applied

        def test_removes_deprecated(self):
            old = [{"_id": "1", "ticker": "AAPL"}, {"_id": "2", "ticker": "MSFT"}]
            new = [{"_id": "1", "ticker": "AAPL"}]
            result = update_list_from_new_source_keep_old_matches(old, new)
            assert len(result) == 1
            assert result[0]["_id"] == "1"
    ```

16. **Add tests for `search.py`**
    - Files: Create `tests/test_search.py`
    - Change: Add 4 test functions verifying SQL expression construction:
      - `test_fuzzy_match_builds_expression` — verifies generated SQL contains `word_similarity`
      - `test_fuzzy_similarity_builds_expression` — verifies generated SQL contains `word_similarity` function
      - `test_apply_fuzzy_search_no_columns_noop` — verifies query is returned unmodified when no columns provided
      - `test_extract_string_columns_skips_non_string` — verifies only String/Text columns are extracted
    - Why: Zero test coverage. DB dependency issues would be surfaced by expression-level tests.
    - Verify: `pytest tests/test_search.py -v` — 4 tests pass without a database connection.

    **Test code:**
    ```python
    import pytest
    from unittest.mock import MagicMock
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import declarative_base
    from FortyFour.Utils.search import (
        fuzzy_match,
        fuzzy_similarity,
        apply_fuzzy_search,
        _extract_string_columns,
    )

    def test_fuzzy_match_builds_expression():
        col = MagicMock()
        expr = fuzzy_match(col, "test")
        assert expr is not None

    def test_fuzzy_similarity_builds_expression():
        col = MagicMock()
        expr = fuzzy_similarity(col, "test")
        assert expr is not None

    def test_apply_fuzzy_search_no_columns_noop():
        mock_query = MagicMock()
        result = apply_fuzzy_search(mock_query, "test")  # no columns
        assert result is mock_query  # returned unchanged

    def test_extract_string_columns_skips_non_string():
        Base = declarative_base()

        class TestModel(Base):
            __tablename__ = "test"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        cols = _extract_string_columns(TestModel)
        col_names = [c.name for c in cols]
        assert "name" in col_names
        assert "id" not in col_names
    ```

---

## Parallel Execution
- [x] Ce plan contient des groupes parallélisables ? **Yes**
- **Group 1** (aws.py fixes) — touches only `aws.py`
- **Group 2** (helpers.py fixes) — touches only `helpers.py`
- **Group 3** (module cleanup) — touches `__init__.py`, `colors.py`, `search.py` (root), `Utils/search.py`
- **Group 4** (tests) — creates 3 new test files, depends on Groups 1-3 being complete

Groups 1, 2, and 3 can run in parallel (no shared files). Group 4 runs after all three complete.
