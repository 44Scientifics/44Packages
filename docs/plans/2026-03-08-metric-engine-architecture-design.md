# Design Document: Metric Engine Architecture for FortyFour.Finance

**Date:** 2026-03-08
**Status:** Approved
**Goal:** Transition from a monolithic `Company` class to a decoupled, cache-first "Metric Engine" architecture optimized for batch processing and complex financial analysis.

## 1. Problem Statement
The current implementation of `Company.py` fetches all SEC data on initialization, re-processes facts for every metric, and couples data fetching with calculation logic. This approach is inefficient for batching hundreds of companies and lacks the flexibility needed for complex time-series analysis and custom metric definitions.

## 2. Architecture Overview

### 2.1 Data Layer: `SECCache` & `Company`
- **`SECCache`**: A SQLite-backed local persistence layer. It stores raw SEC JSON responses keyed by `CIK`. It manages data staleness using a `last_updated` timestamp.
- **`Company`**: A lightweight class that holds a reference to the `SECCache`. Its primary role is to provide a low-level `get_raw_fact(tag_name)` method that returns a Pandas Series for a specific XBRL tag.

### 2.2 Intelligence Layer: `MetricRegistry` & `Formula`
- **`Formula`**: A declarative "recipe" for a financial metric.
    - **`components`**: A priority list of SEC tags for each "part" of the calculation (e.g., `revenue = ["Revenues", "SalesRevenueNet"]`).
    - **`math_func`**: A Python function (e.g., `lambda r, c: (r - c) / r`) applied to the components.
- **`MetricRegistry`**: A central registry where `Formula` objects are defined and stored. This allows the analyst to update "formulas" without changing the data layer.

### 2.3 Execution Layer: `MetricEngine`
- **`MetricEngine`**: The core worker that performs the following steps:
    1. Retrieves the `Formula` from the `MetricRegistry`.
    2. For each component in the formula, it iterates through the priority list of SEC tags, asking the `Company` for data until a match is found.
    3. **Alignment**: Performs an outer join on the `Date` index for all found components to ensure they are synchronized.
    4. **Calculation**: Executes the `math_func` on the aligned data.
    5. Returns a Pandas Series containing the full time-series result.

### 2.4 Batch Processing: `BatchProcessor`
- A utility designed to iterate over a list of `CIKs` and `metrics`. It orchestrates the engine to build a tidy DataFrame (CIK, Date, Metric, Value) for large-scale analysis.

## 3. Data Flow
1. User requests `MetricEngine.calculate(company, "gross_margin")`.
2. Engine looks up the "Gross Margin" formula in `MetricRegistry`.
3. Engine asks `Company` for "Revenues" (trying synonyms) and "COGS" (trying synonyms).
4. `Company` fetches the raw tags from `SECCache` (hitting SQLite, not the SEC API).
5. Engine aligns the "Revenues" and "COGS" Series by Date.
6. Engine applies the formula and returns the result to the User.

## 4. Error Handling
- **`InsufficientDataError`**: Raised if no matching synonyms are found for a critical formula component.
- **Graceful NaNs**: Calculation errors (like division by zero) return `NaN` for specific dates rather than failing the entire batch run.

## 5. Success Criteria
- **Efficiency**: Batch processing of 100+ companies should be significantly faster due to SQLite caching.
- **Extensibility**: Adding a new metric (e.g., "EBITDA Margin") should only require adding a new entry to the `MetricRegistry`.
- **Consistency**: All SEC interaction should follow the same User-Agent and rate-limiting rules through the `SECCache`.
