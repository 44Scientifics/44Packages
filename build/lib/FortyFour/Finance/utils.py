import requests
import pandas as pd
import plotly.express as px


def get_all_cik():
    headers = requests.utils.default_headers()  # type: ignore
    headers.update({'User-Agent': 'My User Agent 1.0', })  # type: ignore
    url = f"https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=headers).json()

    df = pd.DataFrame.from_dict(response).T
    df.rename(columns={"cik_str": "cik", "title": "NAME"}, inplace=True)
    # formatting CIK number

    df["cik"] = df.apply(lambda x: "CIK" + (10 - len(str(x['cik']))) * '0' + str(x['cik']), axis=1)
    df.set_index('ticker', inplace=True)

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


if __name__ == "__main__":
    df = get_all_cik()
    # df_row = df.iloc("AVGO")
    df = df[df.index == "AVGO"]
    print(df)
