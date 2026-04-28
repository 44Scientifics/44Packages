# Metric Engine Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transition the `FortyFour.Finance` package to a decoupled, cache-first architecture for efficient batch processing and complex financial analysis.

**Architecture:** We will implement a SQLite-backed `SECCache`, a lightweight `Company` class for data retrieval, and a `MetricEngine` that uses a `MetricRegistry` of formulas to calculate metrics. The system will handle synonym hunting, date alignment, and batch execution.

**Tech Stack:** Python 3.x, `requests`, `pandas`, `sqlite3`, `plotly`.

---

### Task 1: Implement `SECCache` (Persistence Layer)

**Files:**
- Modify: `src/FortyFour/Finance/utils.py`
- Test: `tests/test_sec_cache.py`

**Step 1: Write the failing test for `SECCache`**
Create `tests/test_sec_cache.py`:
```python
import os
import sqlite3
import json
import pytest
from FortyFour.Finance.utils import SECCache

def test_sec_cache_store_and_retrieve():
    db_path = "test_sec_data.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    cache = SECCache(db_path=db_path)
    test_data = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [{"val": 100, "end": "2023-01-01"}]}}}}}
    cik = "CIK0000000001"
    
    cache.store(cik, test_data)
    retrieved = cache.get(cik)
    
    assert retrieved == test_data
    assert cache.get("non_existent") is None
    
    if os.path.exists(db_path):
        os.remove(db_path)
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_sec_cache.py -v`
Expected: FAIL with `ImportError: cannot import name 'SECCache' from 'FortyFour.Finance.utils'`

**Step 3: Implement `SECCache` in `utils.py`**
Add `SECCache` class to `src/FortyFour/Finance/utils.py`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_sec_cache.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/FortyFour/Finance/utils.py tests/test_sec_cache.py
git commit -m "feat(finance): implement SECCache for local persistence"
```

---

### Task 2: Refactor `request_company_filing` to use `SECCache`

**Files:**
- Modify: `src/FortyFour/Finance/utils.py`

**Step 1: Write the failing test for cached fetching**
Add to `tests/test_sec_cache.py`:
```python
from unittest.mock import patch

def test_request_company_filing_uses_cache():
    cache = SECCache(db_path="test_sec_data_v2.db")
    cik = "CIK0000320193"
    test_data = {"test": "cached"}
    cache.store(cik, test_data)
    
    with patch('requests.get') as mock_get:
        # Should NOT call requests.get if data is in cache
        from FortyFour.Finance.utils import request_company_filing
        res = request_company_filing(cik, cache=cache)
        assert res == test_data
        mock_get.assert_not_called()
    
    if os.path.exists("test_sec_data_v2.db"):
        os.remove("test_sec_data_v2.db")
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_sec_cache.py -v`
Expected: FAIL

**Step 3: Update `request_company_filing` in `utils.py`**
Modify `request_company_filing` in `src/FortyFour/Finance/utils.py` to accept and use a `cache` parameter.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_sec_cache.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/FortyFour/Finance/utils.py
git commit -m "feat(finance): update request_company_filing to support caching"
```

---

### Task 3: Implement Lightweight `Company` and `get_raw_fact`

**Files:**
- Modify: `src/FortyFour/Finance/company.py`
- Test: `tests/test_company_metrics.py`

**Step 1: Write the failing test for `get_raw_fact`**
Create `tests/test_company_metrics.py`:
```python
import pandas as pd
import pytest
import os
from FortyFour.Finance.company import Company
from FortyFour.Finance.utils import SECCache

def test_company_get_raw_fact():
    db_path = "test_sec_company.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    cache = SECCache(db_path=db_path)
    cik = "CIK0000320193"
    test_data = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"val": 100, "end": "2023-01-01", "form": "10-K", "accn": "1"},
                            {"val": 200, "end": "2024-01-01", "form": "10-K", "accn": "2"}
                        ]
                    }
                }
            }
        }
    }
    cache.store(cik, test_data)
    
    company = Company(cik=cik, name="Apple", cache=cache)
    rev_series = company.get_raw_fact("Revenues", filings_type="10-K")
    
    assert len(rev_series) == 2
    assert rev_series.iloc[0] == 100
    assert rev_series.index[0] == pd.to_datetime("2023-01-01")
    
    if os.path.exists(db_path):
        os.remove(db_path)
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_company_metrics.py -v`
Expected: FAIL with `AttributeError`

**Step 3: Update `Company` in `company.py`**
Modify `src/FortyFour/Finance/company.py` to support lazy loading and the `get_raw_fact` method.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_company_metrics.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/FortyFour/Finance/company.py tests/test_company_metrics.py
git commit -m "feat(finance): implement lazy-loading and get_raw_fact for Company"
```

---

### Task 4: Implement `MetricEngine` and `MetricRegistry`

**Files:**
- Create: `src/FortyFour/Finance/engine.py`

**Step 1: Write the failing test for the engine**
Add to `tests/test_company_metrics.py`.

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_company_metrics.py -v`

**Step 3: Implement `engine.py`**
Create `src/FortyFour/Finance/engine.py`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_company_metrics.py -v`

**Step 5: Commit**
```bash
git add src/FortyFour/Finance/engine.py
git commit -m "feat(finance): implement MetricRegistry and MetricEngine"
```

---

### Task 5: Final Cleanup and Exports

**Files:**
- Modify: `src/FortyFour/Finance/__init__.py`

**Step 1: Export new classes**
Update `src/FortyFour/Finance/__init__.py`.

**Step 2: Commit**
```bash
git add src/FortyFour/Finance/__init__.py
git commit -m "chore(finance): export new architecture classes"
```
