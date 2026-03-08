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

from unittest.mock import patch

def test_request_company_filing_uses_cache():
    db_path = "test_sec_data_v2.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    cache = SECCache(db_path=db_path)
    cik = "CIK0000320193"
    test_data = {"test": "cached"}
    cache.store(cik, test_data)
    
    with patch('requests.get') as mock_get:
        # Should NOT call requests.get if data is in cache
        from FortyFour.Finance.utils import request_company_filing
        res = request_company_filing(cik, cache=cache)
        assert res == test_data
        mock_get.assert_not_called()
    
    if os.path.exists(db_path):
        os.remove(db_path)
