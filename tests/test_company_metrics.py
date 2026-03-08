import pandas as pd
import pytest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

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
                            {"val": 100, "end": "2023-01-01", "form": "10-K", "accn": "1", "filed": "2023-02-01"},
                            {"val": 200, "end": "2024-01-01", "form": "10-K", "accn": "2", "filed": "2024-02-01"}
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

from FortyFour.Finance.engine import MetricEngine, MetricRegistry

def test_metric_engine_calculation():
    db_path = "test_sec_engine.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    cache = SECCache(db_path=db_path)
    cik = "CIK0000320193"
    test_data = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [{"val": 100, "end": "2023-01-01", "form": "10-K", "accn": "1", "filed": "2023-02-01"}]
                    }
                },
                "CostOfGoodsSold": {
                    "units": {
                        "USD": [{"val": 60, "end": "2023-01-01", "form": "10-K", "accn": "1", "filed": "2023-02-01"}]
                    }
                }
            }
        }
    }
    cache.store(cik, test_data)
    
    company = Company(cik=cik, name="Apple", cache=cache)
    registry = MetricRegistry()
    registry.register("GrossMargin", 
                      components={"rev": ["Revenues"], "cogs": ["CostOfGoodsSold"]},
                      formula=lambda rev, cogs: (rev - cogs) / rev)
    
    engine = MetricEngine(registry=registry)
    margin = engine.calculate(company, "GrossMargin")
    
    assert len(margin) == 1
    assert margin.iloc[0] == (100 - 60) / 100
    
    if os.path.exists(db_path):
        os.remove(db_path)
