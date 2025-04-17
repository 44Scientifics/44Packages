import json
from functools import cache
import requests
import pandas as pd
import plotly.express as px
import logging
import re
from typing import Optional, Dict, Any


@cache
def get_all_cik() -> pd.DataFrame:
    """
    Fetch all CIKs (Central Index Keys) from the SEC's public API.
    Returns:
        pd.DataFrame: A DataFrame containing CIKs, company names, and tickers.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        'User-Agent': "Mozilla/5.0 (compatible; SEC CIK Fetcher/1.0; +https://www.sec.gov)",
        'Accept': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Use list comprehension for efficiency and clarity
        rows = [
            {
                "cik": f"CIK{int(entry['cik_str']):010d}",
                "NAME": entry["title"],
                "ticker": entry["ticker"]
            }
            for entry in data.values()
        ]
        return pd.DataFrame(rows)
    except Exception as e:
        logging.error(f"Failed to fetch or parse CIK data: {e}")
        return pd.DataFrame(columns=["cik", "NAME", "ticker"])


def create_spark_line(data, _height: int = 100, _width: int = 250):
    """
    Create a sparkline chart using Plotly.
    Args:
        data: Data for the sparkline.
        _height (int): Height of the chart.
        _width (int): Width of the chart.
    Returns:
        Plotly figure object.
    """
    df = None
    if not isinstance(data, pd.DataFrame):
        df = pd.DataFrame(data)

    df = data

    fig = px.area(df, height=_height, width=_width)

    # hide and lock down axes
    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)

    # remove facet/subplot labels
    fig.update_layout(annotations=[], overwrite=True)

    # strip down the rest of the plot
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        margin=dict(t=10, l=10, b=10, r=10))
    fig.update_traces(line_color="#32CD32")

    return fig.show()


def get_company_logo_url(name):
    """
    Generate a TradingView logo URL for a given company name.
    Falls back to a placeholder if the logo does not exist.
    Args:
        name (str): The name of the company.
    Returns:
        str: URL of the company logo or a placeholder.
    """
    base_url = 'https://s3-symbol-logo.tradingview.com/'
    placeholder_url = "https://placehold.co/600x400?text=Logo"

    # Normalize and clean the name
    # Normalize company name: lowercase, remove common suffixes and noise words
    name = name.lower()
    # Remove common noise words and suffixes
    remove_patterns = [
        r"\.com\b", r"\bthe\b", r"\(the\)", r"\bcompany\b", r"\bgroup\b"
    ]
    for pattern in remove_patterns:
        name = re.sub(pattern, "", name)
    name = name.strip()

    # Remove extra spaces and special characters
    name = re.sub(r"[']", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    suffixes = [
        "corp.", "corporation", "inc", "incorporated", "inc.", "(the)",
        "limited", "ltd", "plc", "laboratories", "communications", "the",
        "company", ".com", " company", "new", "motor", "ag"
    ]

    words = name.split()
    if words and words[-1] in suffixes:
        words[-1] = '-big.svg'
        logo_name = '-'.join(words)
    else:
        logo_name = '-'.join(words) + '--big.svg'

    # Replace 'and' and '&' with '-'
    logo_name = logo_name.replace('and', '-').replace('&', '-')

    logo_url = f"{base_url}{logo_name}"

    try:
        response = requests.head(logo_url, timeout=2)
        if response.status_code == 200:
            return logo_url
    except requests.RequestException:
        pass

    return placeholder_url


def request_company_filing(cik: str) -> Optional[Dict[str, Any]]:
    """
    Fetch company filing data from the SEC XBRL API for a given CIK.
    Args:
        cik (str): The Central Index Key (CIK) of the company, e.g., 'CIK0000320193'.
    Returns:
        dict or None: The JSON response as a dictionary if successful, None otherwise.
    """
    if not (isinstance(cik, str) and cik.startswith('CIK') and cik[3:].isdigit() and len(cik) == 13):
        logging.error(f"Invalid CIK format: {cik}")
        return None

    url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; SEC Filing Fetcher/1.0; +https://www.sec.gov)',
        'Accept': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as e:
        logging.error(f"Failed to fetch or parse filing for {cik}: {e}")
        return None


ACCOUNTING_NORM_EXCLUDE = {"srt", "invest", "dei"}

if __name__ == "__main__":
    cik = "320193"  # Apple Inc.
    response = request_company_filing(cik)
    if response and "facts" in response:
        accounting_norm_list = [x for x in response["facts"].keys() if x not in ACCOUNTING_NORM_EXCLUDE]
        print(f"Accounting norms found for {cik}: {accounting_norm_list}")
    else:
        print(f"No facts found in SEC response for {cik}.")
    print(response)

