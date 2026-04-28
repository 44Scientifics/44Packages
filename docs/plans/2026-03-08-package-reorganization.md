# Package Reorganization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate the `FortyFour` package by removing redundant files and exposing key utilities at the sub-package level for cleaner imports.

**Architecture:** We will move from a deep file-based import structure to a sub-package export structure using `__init__.py`. This involves renaming `company_v3.py` to `company.py` and updating `__init__.py` files to export common symbols.

**Tech Stack:** Python 3.x, `setuptools`.

---

### Task 1: Consolidate Finance Company Files

**Files:**
- Modify: `src/FortyFour/Finance/company_v3.py` (rename)
- Delete: `src/FortyFour/Finance/company.py`

**Step 1: Delete the old company.py**
Run: `rm src/FortyFour/Finance/company.py`

**Step 2: Rename company_v3.py to company.py**
Run: `mv src/FortyFour/Finance/company_v3.py src/FortyFour/Finance/company.py`

**Step 3: Verify the move**
Run: `ls src/FortyFour/Finance/`
Expected: `__init__.py`, `company.py`, `utils.py`

**Step 4: Commit**
```bash
git add src/FortyFour/Finance/
git commit -m "refactor(finance): consolidate company_v3 into company.py"
```

---

### Task 2: Setup Finance Sub-package Exports

**Files:**
- Modify: `src/FortyFour/Finance/__init__.py`

**Step 1: Update __init__.py with exports**
```python
from .company import Company, GAAP
from .utils import (
    get_all_cik, 
    calculate_cagr, 
    get_company_logo_url, 
    create_spark_line,
    request_company_filing
)
```

**Step 2: Verify imports with a script**
Create `verify_finance.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath("src"))
from FortyFour.Finance import Company, GAAP, get_all_cik

print("Finance imports successful")
```
Run: `python3 verify_finance.py`
Expected: "Finance imports successful"

**Step 3: Commit**
```bash
git add src/FortyFour/Finance/__init__.py
git commit -m "feat(finance): add top-level exports to __init__.py"
```

---

### Task 3: Setup Utils Sub-package Exports

**Files:**
- Modify: `src/FortyFour/Utils/__init__.py`

**Step 1: Update __init__.py with exports**
```python
from .aws import upload_to_s3, read_file_from_s3
from .helpers import serialize_date_in_dict, remove_nan_values_from_dict
```

**Step 2: Verify imports with a script**
Create `verify_utils.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath("src"))
from FortyFour.Utils import upload_to_s3, serialize_date_in_dict

print("Utils imports successful")
```
Run: `python3 verify_utils.py`
Expected: "Utils imports successful"

**Step 3: Commit**
```bash
git add src/FortyFour/Utils/__init__.py
git commit -m "feat(utils): add top-level exports to __init__.py"
```

---

### Task 4: Cleanup and Final Verification

**Step 1: Remove verification scripts**
Run: `rm verify_finance.py verify_utils.py`

**Step 2: Final check of the directory structure**
Run: `ls -R src/FortyFour`

**Step 3: Commit**
```bash
git commit --allow-empty -m "chore: package reorganization complete"
```
