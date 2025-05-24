import json
from functools import cache
import requests
import pandas as pd
import plotly.express as px
import logging
import re

@cache
def get_all_cik():
    headers = {
        'User-Agent': "Mozilla/5.0 (compatible; SEC-DataFetcher/1.0)",
        'Accept': 'application/json'
    }
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame.from_dict(data, orient='index')
        df.rename(columns={"cik_str": "cik", "title": "NAME"}, inplace=True)
        df["cik"] = df["cik"].apply(lambda x: f"CIK{int(x):010d}")
        return df
    except Exception as e:
        logging.error(f"Failed to fetch CIK data: {e}")
        return pd.DataFrame()


def create_spark_line(data, _height: int = 100, _width: int = 250):
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
    """

    base_url = 'https://s3-symbol-logo.tradingview.com/'
    # Normalize name: lowercase, remove unwanted words, punctuation, and extra spaces
    name = name.lower()
    name = re.sub(r'\b(the|company|group|corp\.?|corporation|inc\.?|incorporated|ltd\.?|plc|laboratories|communications|new|motor|ag|\.com)\b', '', name)
    name = re.sub(r'[&]', 'and', name)
    name = re.sub(r"[^a-z0-9\s-]", '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    clean_name = '-'.join(name.split())
    logo_url = f"{base_url}{clean_name}--big.svg"
    try:
        resp = requests.head(logo_url, timeout=2)
        if resp.status_code == 200:
            return logo_url
    except Exception:
        pass
    return "https://placehold.co/600x400?text=Logo"


def request_company_filing(cik: str) -> json:
    # Get a copy of the default headers that requests would use
    #headers = requests.utils.default_headers()  # type: ignore
    # headers.update({'User-Agent': 'My User Agent 1.0', })  # type: ignore

    headers = {
        'User-Agent': 'My User Agent 1.0',
        'accept': 'application/json'
    }
    url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"
    response = requests.get(url, headers=headers)
    return response.json()

def calculate_cagr(df: pd.Series, periods: int):
    if len(df) < 2:
        return 0
    start_value = df.iloc[-periods-1]
    if start_value == 0:
        return 0
    end_value = df.iloc[-1]
    cagr = (end_value / start_value) ** (1 / periods)-1
    return round(cagr*100,2)


if __name__ == "__main__":
    print(get_all_cik())
    response = request_company_filing("CIK0000320193")
    accounting_norm_list = [x for x in [*response["facts"].keys()] if x not in ["srt", "invest", "dei"]]
    print(accounting_norm_list)