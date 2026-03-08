import os
import sqlite3
import json
import pytest
import sys

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

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
