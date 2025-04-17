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
   
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
        'Accept': 'application/json'
    }
    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=headers)

    response = response.json()
    df = pd.DataFrame.from_dict(response).T
    df.rename(columns={"cik_str": "cik", "title": "NAME"}, inplace=True)
    # formatting CIK number
    df["cik"] = df["cik"].apply(lambda x: f"CIK{int(x):010d}" if pd.notnull(x) else None)
    return df




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


def request_company_filing(cik: str) -> json:
    # Get a copy of the default headers that requests would use
    #headers = requests.utils.default_headers()  # type: ignore
    # headers.update({'User-Agent': 'My User Agent 1.0', })  # type: ignore

    # check if the CIK is valid
    if not cik.startswith("CIK"):
        cik = "CIK" + str(cik).zfill(10)

    headers = {
        'User-Agent': 'My User Agent 1.0',
        'accept': 'application/json'
    }
    url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"
    response = requests.get(url, headers=headers)
    return response.json()


ACCOUNTING_NORM_EXCLUDE = {"srt", "invest", "dei"}

if __name__ == "__main__":
    cik = "CIK0000320193"  # Apple Inc.
    response = request_company_filing(cik)
    if response and "facts" in response:
        accounting_norm_list = [x for x in response["facts"].keys() if x not in ACCOUNTING_NORM_EXCLUDE]
        print(f"Accounting norms found for {cik}: {accounting_norm_list}")
    else:
        print(f"No facts found in SEC response for {cik}.")
    print(get_all_cik())

