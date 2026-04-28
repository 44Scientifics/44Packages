# FortyFour: Advanced Financial Analysis for SEC Data

`FortyFour` is a high-performance Python library designed for quantitative financial analysis of SEC EDGAR data. It provides a decoupled, cache-first architecture that simplifies the process of fetching, persisting, and calculating complex financial metrics for thousands of public companies.

---

## 🚀 Key Features

-   **SQLite-Backed Persistence**: High-speed local cache (`SECCache`) to store raw SEC JSON responses, ensuring compliance with SEC rate limits and near-instant subsequent runs.
-   **Declarative Metric Engine**: Define complex financial formulas once in a `MetricRegistry` and execute them across any company.
-   **Automated Synonym Hunting**: Built-in logic to search through multiple XBRL tags (synonyms) to find the best match for a given metric.
-   **Intelligent Time-Series Alignment**: Automatically handles disparate fiscal year ends and reporting dates by aligning data on a common Pandas index.
-   **Lazy Loading**: Only fetches data from the cache or the SEC API when a specific fact or metric is actually requested.

---

## 📦 Installation

To install the package, clone the repository and install it in editable mode:

```bash
git clone https://github.com/44Scientifics/44Packages.git
cd 44Packages
pip install .
```

---

## 🧪 Finance Module Deep Dive

The `FortyFour.Finance` module is built on a four-tier architecture designed for scalability and analytical depth.

### 1. The Persistence Tier (`SECCache`)
The `SECCache` is the heart of the library's performance. It manages a local SQLite database that stores the full "Company Facts" JSON response from the SEC.

-   **Mechanism**: When you request data for a CIK, the system checks the local SQLite database first. If the data is missing or older than the `max_age_days` (default: 1), it fetches a fresh copy from the SEC API and stores it.
-   **Benefit**: This allows you to perform complex analysis over hundreds of companies while making only **one API call per company**.

```python
from FortyFour.Finance import SECCache

# db_path defaults to "sec_data.db"
cache = SECCache(db_path="my_financial_data.sqlite")
```

### 2. The Data Tier (`Company`)
The `Company` class provides a high-level interface to the raw XBRL facts stored in the cache.

-   **CIK Normalization**: Accepts CIKs as integers, unpadded strings (`"320193"`), or padded strings (`"0000320193"`).
-   **Lazy Loading**: The heavy `filing_data` (the raw JSON) is only loaded into memory the first time you request a fact.
-   **`get_raw_fact(tag_name, filings_type)`**: Retrieves a specific XBRL tag (e.g., `Assets`, `NetIncomeLoss`) as a Pandas Series indexed by `Date`.

```python
from FortyFour.Finance import Company

# CIK 320193 is Apple Inc.
apple = Company(cik=320193, name="Apple", cache=cache)

# Get historical Total Assets from 10-K filings
assets_history = apple.get_raw_fact("Assets", filings_type="10-K")
print(assets_history)
```

### 3. The Logic Tier (`MetricRegistry`)
Financial reporting is inconsistent. One company reports "Revenue", another "SalesRevenueNet". The `MetricRegistry` solves this by allowing you to define metrics as "formulas" with a priority list of synonyms.

-   **Synonym Hunting**: The engine will try each synonym in the list until it finds a tag with data.
-   **Formula Support**: Formulas are standard Python functions that can take multiple inputs.

```python
from FortyFour.Finance import MetricRegistry

registry = MetricRegistry()

# Define "Gross Margin"
registry.register(
    "Gross Margin",
    components={
        "rev": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
        "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"]
    },
    formula=lambda rev, cogs: (rev - cogs) / rev
)
```

### 4. The Execution Tier (`MetricEngine`)
The `MetricEngine` brings everything together.

-   **Automatic Alignment**: If you calculate a metric requiring two different tags (e.g., `NetIncome` and `TotalAssets` for ROA), the engine performs an **outer join** on their dates and forward-fills data to ensure the calculation is mathematically sound.
-   **Error Resilience**: If a required component is missing after trying all synonyms, it logs a warning and returns an empty Series instead of crashing the batch.

```python
from FortyFour.Finance import MetricEngine

engine = MetricEngine(registry=registry)
gm_series = engine.calculate(apple, "Gross Margin", filings_type="10-K")
```

---

## 📊 Batch Processing Example

To perform analysis on a list of companies, you can simply iterate and collect results into a single DataFrame.

```python
ciks = ["320193", "789019", "1018724"] # Apple, Microsoft, Amazon
metrics = ["Gross Margin", "Debt-to-Equity"]

all_results = []

for cik in ciks:
    co = Company(cik=cik, name=f"Company_{cik}", cache=cache)
    for m in metrics:
        series = engine.calculate(co, m)
        if not series.empty:
            res_df = series.to_frame(name="value")
            res_df["CIK"] = cik
            res_df["Metric"] = m
            all_results.append(res_df)

final_df = pd.concat(all_results).reset_index()
# final_df now has [Date, value, CIK, Metric]
```

---

## 🛠️ Utils & Helpers

The `Finance` module also includes several utilities in `utils.py`:

-   **`get_all_cik()`**: Fetches the master list of all current SEC tickers and CIKs.
-   **`calculate_cagr(series, periods)`**: Robust CAGR calculation with error handling for negative values or insufficient data.
-   **`get_company_logo_url(name)`**: Generates a TradingView logo URL with automated name cleaning.
-   **`create_spark_line(data)`**: Generates a clean, interactive Plotly sparkline for quick visualization.

---

## 🤝 Contributing

Contributions are welcome! Please submit a pull request or open an issue for suggestions or bugs.

## 📜 License

Distributed under the MIT License.
