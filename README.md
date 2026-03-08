# FortyFour

A comprehensive Python library for financial analysis and general utilities, designed for high-performance batch processing and complex metric calculation.

## Description

`FortyFour` provides a decoupled, cache-first architecture for interacting with SEC EDGAR data. It features a **Metric Engine** that allows analysts to define declarative formulas for financial metrics, which the engine then calculates by automatically searching through SEC XBRL synonyms and aligning time-series data.

## Key Features

- **Local Persistence**: SQLite-backed `SECCache` to store raw SEC JSON responses, ensuring high speed and compliance with SEC rate limits.
- **Metric Engine**: De-coupled calculation logic using `MetricRegistry` and `MetricEngine`.
- **Flexible Synonyms**: Formulas define priority lists of SEC tags to handle inconsistent reporting across companies.
- **Lazy Loading**: Data is only fetched from the cache or API when a specific fact or metric is requested.

## Installation

```bash
git clone https://github.com/44Scientifics/44Packages.git
cd 44Packages
pip install .
```

## Quick Start (Finance)

```python
import pandas as pd
from FortyFour.Finance import Company, SECCache, MetricRegistry, MetricEngine

# 1. Initialize Cache and Registry
cache = SECCache(db_path="my_finance_cache.sqlite")
registry = MetricRegistry()

# 2. Define a custom Formula
registry.register(
    "Gross Margin",
    components={
        "rev": ["Revenues", "SalesRevenueNet"],
        "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"]
    },
    formula=lambda rev, cogs: (rev - cogs) / rev
)

# 3. Calculate for a Company
engine = MetricEngine(registry=registry)
apple = Company(cik="0000320193", name="Apple Inc.", cache=cache)

gross_margin = engine.calculate(apple, "Gross Margin", filings_type="10-K")
print(gross_margin.tail())
```

## Modules

### `FortyFour.Finance`
- `company.py`: Lightweight `Company` class for data retrieval and lazy loading.
- `engine.py`: `MetricEngine` and `MetricRegistry` for formula execution.
- `utils.py`: `SECCache`, SEC API interaction, and financial helpers (e.g., CAGR).
- `etf.py`: Tools for working with Exchange Traded Funds.

### `FortyFour.Utils`
- `aws.py`: Helpers for AWS S3 interaction.
- `colors.py`: Terminal output color utilities.
- `helpers.py`: General dictionary and date manipulation.

## Dependencies

- `pandas`: Data manipulation and time-series alignment.
- `requests`: SEC API interaction.
- `sqlite3`: Local data persistence.
- `plotly`: Financial visualization.

## Author

44 SCIENTIFICS LTD (44scientifics@gmail.com)

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for suggestions or bugs.

## License

MIT License (recommended)
