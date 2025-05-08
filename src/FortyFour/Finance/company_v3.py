import json
from functools import cache
import requests
import pandas as pd
import plotly.express as px
import logging
import re

from typing import List, Tuple, Optional

from gaap_synonyms import GAAP

def request_company_filing(cik: str) -> json:
    # Get a copy of the default headers that requests would use
    #headers = requests.utils.default_headers()  # type: ignore
    # headers.update({'User-Agent': 'My User Agent 1.0', })  # type: ignore

    headers = {
        'User-Agent': 'My User Agent 1.0', # It's good practice to identify your client
        'accept': 'application/json'
    }
    url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"
    response = requests.get(url, headers=headers)
    response.raise_for_status() # Raise an exception for HTTP errors
    return response.json()


class Company:
    """
    A class representing a company with its CIK and name.
    """
    def __init__(self, cik: str, name: str):
        self.cik = "CIK"+str(cik).zfill(10)  # Ensure CIK is 10 digits
        self.name = name

        # request the company filing data
        headers = {
        'User-Agent': 'My User Agent 1.0', # It's good practice to identify your client
        'accept': 'application/json'
        }
        url = f"https://data.sec.gov/api/xbrl/companyfacts/{self.cik}.json"
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors
        self.filing_data = response.json()




    def get_financial(self, gaap_concept: GAAP, filings_type: str ="10-Q") -> pd.DataFrame:
        
        cik = self.cik

        try:
            data = request_company_filing(cik)
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch data for CIK {cik}: {e}")
            return pd.DataFrame() # Return empty DataFrame on error
        
        canonical_name = gaap_concept.value[0]
        synonyms = gaap_concept.value[1]
        
        collected_entries = []
        # Check canonical name first
        if data.get("facts") and data["facts"].get("us-gaap") and canonical_name in data["facts"]["us-gaap"]:
            if "units" in data["facts"]["us-gaap"][canonical_name] and "USD" in data["facts"]["us-gaap"][canonical_name]["units"]:
                for entry in data["facts"]["us-gaap"][canonical_name]["units"]["USD"]:
                    entry_copy = entry.copy() 
                    entry_copy['source_key'] = canonical_name 
                    entry_copy['is_canonical'] = True
                    collected_entries.append(entry_copy)

        # Then check synonyms
        for key in synonyms:
            if data.get("facts") and data["facts"].get("us-gaap") and key in data["facts"]["us-gaap"]:
                if "units" in data["facts"]["us-gaap"][key] and "USD" in data["facts"]["us-gaap"][key]["units"]:
                    for entry in data["facts"]["us-gaap"][key]["units"]["USD"]:
                        entry_copy = entry.copy()
                        entry_copy['source_key'] = key
                        entry_copy['is_canonical'] = False
                        collected_entries.append(entry_copy)

        if not collected_entries:
            logging.info(f"No data found for {gaap_concept.name} for CIK {cik} using specified keys.")
            return pd.DataFrame()

        # Filter by the specified filings type
        filtered_by_form = [entry for entry in collected_entries if entry.get("form") == filings_type]

        if not filtered_by_form:
            logging.info(f"No data found for {gaap_concept.name} for CIK {cik} with form type {filings_type}.")
            return pd.DataFrame()
            
        # Sort entries to prepare for deduplication.
        # Priority: end date, value, canonical status (True first), then filed date (earliest first).
        processed_entries = sorted(
            filtered_by_form,
            key=lambda x: (
                x.get('end', ''), 
                x.get('val', 0), 
                not x.get('is_canonical', False), # True (canonical) sorts before False (synonym)
                x.get('filed', '') # Earliest filed date first as a tie-breaker
            )
        )

        deduplicated_entries = []
        seen_unique_key = set() # To track (end_date, value, form) combinations

        for entry in processed_entries:
            # Define uniqueness based on 'end', 'val', and 'form'.
            # The sorting ensures that for any (end, val, form) group,
            # the preferred entry (canonical, or earliest filed synonym) is processed first.
            unique_key = (entry.get('end'), entry.get('val'), entry.get('form'))
            
            if unique_key not in seen_unique_key:
                deduplicated_entries.append(entry)
                seen_unique_key.add(unique_key)
                
        if not deduplicated_entries:
            logging.info(f"No unique data entries found after processing for {gaap_concept.name} for CIK {cik} with form type {filings_type}.")
            return pd.DataFrame()

        df = pd.DataFrame(deduplicated_entries)
        # Select and order columns for the final DataFrame
        #df = df[["end", "val", "accn", "form","", "source_key", "is_canonical"]]
        df["end"] = pd.to_datetime(df["end"], format="%Y-%m-%d", errors='coerce')
        # Final sort by end date for presentation
        df = df.sort_values(by="end").reset_index(drop=True)
        
        return df


if __name__ == "__main__":
    # Create a Company instance
    apple_cik = 1141391

    company = Company(cik=apple_cik, name="Apple Inc.")
    # Example CIK for Apple Inc.
    capex_df = company.get_financial(gaap_concept=GAAP.CAPEX, filings_type="10-K")
    cash_df = company.get_financial(gaap_concept=GAAP.CASH_CASH_EQUIVALENTS, filings_type="10-K")
    print(capex_df)
    print("" * 20)
    print(cash_df)
    