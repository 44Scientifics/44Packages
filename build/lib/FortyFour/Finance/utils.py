from functools import cache
import requests
import pandas as pd
import plotly.express as px
import requests_cache
from datetime import timedelta




def get_all_cik():
    headers = requests.utils.default_headers()  # type: ignore
    headers.update({'User-Agent': 'My User Agent 1.0', })  # type: ignore
    _url = "https://www.sec.gov/files/company_tickers.json"
    session = requests_cache.CachedSession('demo_cache')
    response = session.get(url=_url,headers=headers, expire_after=timedelta(hours=1)).json()
    #response = requests.get(url, headers=headers).json()
    df = pd.DataFrame.from_dict(response).T
    df.rename(columns={"cik_str": "cik", "title": "NAME"}, inplace=True)
    # formatting CIK number

    df["cik"] = df.apply(lambda x: "CIK" + (10 - len(str(x['cik']))) * '0' + str(x['cik']), axis=1)
    
    return df


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
    
    url = 'https://s3-symbol-logo.tradingview.com/'
    name = str.lower(name)
    word_to_remove = [".com", "the ", " (the)", 'company', 'group']
    for item in word_to_remove:
        if item in name:
            name = name.replace(item, "")

    suffix = name.split()

    suffix_list = ["corp.", "corporation", "inc",'incorporated','inc.','(the)'
                   "limited", "ltd",'plc', "laboratories", "communications", 'the', "company", ".com", " company", "new", 'motor','ag']

    if suffix[-1] in suffix_list:
        name = name.replace(suffix[-1], '-big.svg')
        name = name.replace(' ', '-')
        name = name.replace('and', '-')
        name = name.replace('&', '-')
        name = name.replace("'", '')
        result = f"{url}{name}"
        #print(result)
        return result
    else:
        name = name+'--big.svg'
        name = name.replace(' ', '-')
        name = name.replace('and', '-')
        name = name.replace("'", '')
        name = name.replace('&', '-')
        
        result = f"{url}{name}"
        #print(result)
        return result

def request_company_filing(cik:str)-> requests.Response:
    # Get a copy of the default headers that requests would use
    headers = requests.utils.default_headers()  # type: ignore
    headers.update({'User-Agent': 'My User Agent 1.0', })  # type: ignore
    url = f"https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"
    response = requests.get(url, headers=headers).json()
    return response


if __name__ == "__main__":
    print(get_all_cik())
