import json
from functools import cache
import requests
import pandas as pd
import plotly.express as px
import logging
import re
import sqlite3
import time

# SEC EDGAR requires a User-Agent that identifies the user (Name and Email)
DEFAULT_HEADERS = {
    'User-Agent': "FortyFour Scientifics (admin@fortyfour.com)",
    'Accept': 'application/json'
}

class SECCache:
    """
    A SQLite-backed cache for SEC EDGAR company facts.
    """
    def __init__(self, db_path="sec_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sec_cache (
                    cik TEXT PRIMARY KEY,
                    data TEXT,
                    last_updated REAL
                )
            """)

    def get(self, cik, max_age_days=1):
        """
        Retrieve cached data for a CIK if it's within the max age.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data, last_updated FROM sec_cache WHERE cik = ?", (cik,))
            row = cursor.fetchone()
            if row:
                data_str, last_updated = row
                if (time.time() - last_updated) / 86400 <= max_age_days:
                    return json.loads(data_str)
        return None

    def store(self, cik, data):
        """
        Store data in the cache for a CIK.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sec_cache (cik, data, last_updated) VALUES (?, ?, ?)",
                (cik, json.dumps(data), time.time())
            )

@cache
def get_all_cik():
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
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
    """
    Creates and shows a Plotly sparkline for the given data.
    """
    if isinstance(data, pd.DataFrame):
        df = data
    else:
        df = pd.DataFrame(data)

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
        # Using a browser-like User-Agent for logos might be better
        logo_headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.head(logo_url, headers=logo_headers, timeout=2)
        if resp.status_code == 200:
            return logo_url
    except Exception:
        pass
    return "https://placehold.co/600x400?text=Logo"


def request_company_filing(cik: str, cache: SECCache = None) -> dict:
    """
    Fetch company facts from SEC EDGAR API for a given CIK.
    """
    # Ensure CIK is correctly formatted
    cik_str = str(cik).zfill(10)
    if not cik_str.startswith("CIK"):
        cik_str = f"CIK{cik_str}"
        
    if cache:
        cached_data = cache.get(cik_str)
        if cached_data:
            return cached_data
            
    url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik_str}.json"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if cache:
            cache.store(cik_str, data)
        return data
    except Exception as e:
        logging.error(f"Failed to fetch filing data for {cik_str}: {e}")
        return {}

def calculate_cagr(df: pd.Series, periods: int):
    """
    Calculate the Compound Annual Growth Rate over the given number of periods.
    """
    if len(df) < periods + 1:
        logging.warning(f"Insufficient data to calculate CAGR over {periods} periods (only {len(df)} points available)")
        return 0
    
    start_value = df.iloc[-periods-1]
    end_value = df.iloc[-1]
    
    if start_value <= 0 or end_value <= 0:
        return 0
        
    cagr = (end_value / start_value) ** (1 / periods) - 1
    return round(cagr * 100, 2)


if __name__ == "__main__":
    print(get_all_cik().head())
    response = request_company_filing("0000320193")
    if response and "facts" in response:
        accounting_norm_list = [x for x in response["facts"].keys() if x not in ["srt", "invest", "dei"]]
        print(f"Available fact types: {accounting_norm_list}")
    else:
        print("Failed to fetch data.")
