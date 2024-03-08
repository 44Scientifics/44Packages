import logging

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly import plot
from functools import reduce
from FortyFour.Finance.utils import get_all_cik, request_company_filing


class Company:
    # Initial initialization method
    def __init__(self, ticker):
        self.ticker = str.upper(ticker)
        df = get_all_cik()
        df.set_index('ticker', inplace=True)

        df = df[df.index == self.ticker]

        self.cik = df["cik"].values[0]
        self.response = request_company_filing(self.cik)

        # for example us-gaap or ifrs etc...
        accounting_norm_list = [x for x in [*self.response['facts']] if x not in ["srt", "invest"]]

        self.GAAP_NORM = accounting_norm_list[1]

        company_name = self.response['entityName']
        self.company_name = company_name
        self.gaap_List = self.response['facts'][self.GAAP_NORM].keys()

    # def get_gaap_list(self):
    #
    #     print(f'get_gaap_list() called for : CIK: {self.cik}, {self.company_name}')
    #
    #     gaaplist = self.response['facts'][self.GAAP_NORM]
    #
    #     return gaaplist
    def compounding_annual_growth_rate(self, df, nb_years, inline_graph=False):
        # Check if the data is a dataframe:
        is_dataframe = isinstance(df, pd.DataFrame)
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        if len(df.index) >= (nb_years + 1):
            ending_value = df.iloc[-1][0]
            beginning_value = df.iloc[-nb_years - 1][0]
            try:
                result = round(
                    ((ending_value / beginning_value) ** (1 / nb_years) - 1), 3) * 100
            except Exception as e:
                logging.warning('The function compounding_annual_growth_rate() encounter an exeption: ', e)
                result = 0

            fig = go.Figure(go.Indicator(
                domain={'x': [0, 1], 'y': [0, 1]},
                value=result,
                mode="gauge+number+delta",
                title={
                    'text': f"{self.company_name}<br><sup> {nb_years}-Years GAGR</sup>"},
                delta={'reference': 10},
                gauge={'axis': {'range': [-20, 20]},
                       'steps': [
                           {'range': [-20, 0], 'color': "pink"},
                           {'range': [0, 5], 'color': "gray"},
                           {'range': [5, 10], 'color': "lightcyan"},
                           {'range': [10, +20], 'color': "lightgreen"}
                       ],
                       'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 10}}))

            if inline_graph:  # usefully in jupyter notebook
                fig.show()

            return fig
        else:
            fig = go.Figure(go.Indicator(
                domain={'x': [0, 1], 'y': [0, 1]},
                value=0,
                mode="gauge+number+delta",
                title={
                    'text': f"{self.company_name}<br><sup>No Data for {nb_years}-Years GAGR</sup>"},
                delta={'reference': 0},
                gauge={'axis': {'range': [0, 20]},
                       'steps': [

                       ],
                       }))

            return fig

    def Financials(self, selected_gaap: [], form_type=None):
        '''Select a list of gaap and the function will return a dataframe ot the selected gaaps'''

        df_list_to_merge = []

        for gaap in selected_gaap:
            df = pd.DataFrame()
            # print(GAAP_NORM)
            try:  # try gaap norm
                gaap_unit = list(self.response['facts'][self.GAAP_NORM][gaap]['units'].keys())[
                    -1]  # sometimes it can be multiple currencies so I select the last
                df = pd.DataFrame.from_records(
                    self.response['facts'][self.GAAP_NORM][gaap]["units"][gaap_unit]).dropna()
            except Exception as e:  # try dei
                # sometimes it can be multiple currencies so I select the last
                gaap_unit = list(self.response['facts']["dei"][gaap]['units'].keys())[-1]
                df = pd.DataFrame.from_records(self.response['facts']["dei"][gaap]["units"][gaap_unit])
                print(f"An exception occurred while retrieving {gaap}", e)
            df.rename(columns={'val': gaap, 'end': 'Date'}, errors="ignore", inplace=True)

            # We want to drop the column only if it exists by using errors='ignore'
            df.drop(['accn', 'fy', 'fp', 'form', 'filed', 'start'], errors='ignore', axis=1, inplace=True)

            # if "frame column exists":
            if "frame" in df.columns:
                df = df.dropna(axis=0)
                match form_type:
                    case "10-Q":
                        df = df[df["frame"].str.contains('Q')]
                        df.drop(['frame'], axis=1, inplace=True)
                        df_list_to_merge.append(df)
                    case "10-K":
                        df = df[~df["frame"].str.contains('Q')]
                        df.drop(["frame"], axis=1, inplace=True)
                        df_list_to_merge.append(df)

                    case "20-F":
                        df = df[~df["frame"].str.contains('Q')]
                        df.drop(["frame"], axis=1, inplace=True)
                        df_list_to_merge.append(df)

                    case "20-F/A":
                        df = df[~df["frame"].str.contains('Q')]
                        df.drop(["frame"], axis=1, inplace=True)
                        df_list_to_merge.append(df)

                    case _:
                        df.drop(["frame"], axis=1, inplace=True)
                        df_list_to_merge.append(df)
                        pass
                # df.set_index('Date', inplace=True)
            else:
                pass

        final_df = reduce(lambda left, right: pd.merge(left, right, on=['Date'], how='outer'), df_list_to_merge)

        final_df['Date'] = pd.to_datetime(final_df['Date'])
        final_df.set_index('Date', inplace=True)
        final_df.sort_values(by="Date", inplace=True)
        return final_df

    def CommonStockSharesOutstanding(self, form_type="10-K"):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List(display=False)

        synonyms = ['CommonStockSharesIssued', 'EntityCommonStockSharesOutstanding', 'NumberOfSharesOutstanding',
                    'NumberOfSharesIssuedAndFullyPaid', "WeightedAverageShares",
                    "WeightedAverageNumberOfDilutedSharesOutstanding", "CommonStockSharesOutstanding",
                    'NumberOfSharesIssuedAndFullyPaid']
        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        if df.empty:
            df = self.Financials(list, form_type='10-Q')
            df = df.resample('BY').last()

        df['NumberOfSharesOutstanding'] = df.sum(axis=1)

        return df['NumberOfSharesOutstanding']

    def MarketCap(self, form_type="10-Q"):
        df = self.Financials(["EntityPublicFloat"], form_type="10-Q")
        return df

    def Equity(self, form_type="10-K"):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                    'Equity', 'StockholdersEquity', 'EquityAttributableToOwnersOfParent']

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['Equity'] = df.sum(axis=1)
        df['Repetition'] = df.notnull().sum(axis=1) - 1
        df['Equity'] = df['Equity'] / df['Repetition']

        return df

    def AssetsLiabilitiesEquity(self, form_type="10-Q", show_graph=False):
        df = pd.DataFrame()
        df['Assets'] = self.Financials(["Assets"], form_type=form_type)["Assets"]
        df["Equity"] = self.Equity(form_type=form_type)["Equity"]
        df["Liabilities"] = df['Assets'] - df["Equity"]
        df['LiabilitiesToAssetsRatio'] = df["Liabilities"] / df['Assets']

        fig = px.area(df, x=df.index, y=['LiabilitiesToAssetsRatio'],
                      title=f"{self.company_name}<br><sup>Liabilities To Assets Ratio</sup>",
                      line_shape="spline",
                      template="seaborn",
                      )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          # width=1200,
                          # height=500,
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))
        fig.update_traces(line_color="darksalmon")
        # fig.update_layout({'plot_bgcolor': 'rgba(0,0,0,0)','paper_bgcolor': 'rgba(0,0,0,0)'})

        if show_graph == True:
            fig.show()

        return df, fig

    def Capex(self, form_type="10-K"):

        list = []
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        for item in ['PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
                     "PaymentsToAcquireRealEstateHeldForInvestment", "PaymentsToDevelopRealEstateAssets",
                     "PaymentsForCapitalImprovements", 'PaymentsToAcquireAndDevelopRealEstate',
                     "PaymentsToAcquireRealEstate", "PaymentsToAcquireCommercialRealEstate",
                     "PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
                     "PaymentsToAcquireOtherPropertyPlantAndEquipment",
                     "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
                     "PurchaseOfPropertyPlantAndEquipmentAndIntangibleAssets",
                     "PurchasesOfPropertyAndEquipmentAndIntangibleAssets"]:

            if item in gaaplist:
                list.append(item)

        df = self.Financials(list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['CAPEX'] = df.sum(axis=1)

        return df

    def PropertyPlantAndEquipmentGross(self, form_type="10-Q"):
        my_list = []
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        for item in ["PropertyPlantAndEquipmentGross", 'PropertyPlantAndEquipment',
                     "RealEstateInvestmentPropertyAtCost", "GrossInvestmentInRealEstateAssets"]:
            if item in gaaplist:
                my_list.append(item)

        if len(my_list) == 0:
            my_list.append('PropertyPlantAndEquipmentNet')
            # df = self.Financials(my_list, form_type=form_type)

        df = self.Financials(my_list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['PropertyPlantAndEquipmentsGross'] = df.sum(axis=1)
        return df

    def PropertyPlantAndEquipmentNet(self, form_type="10-Q"):
        list = []
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        for item in ["PropertyPlantAndEquipmentNet", 'RealEstateInvestmentPropertyNet',
                     'NetInvestmentInRealEstateAssets']:
            if item in gaaplist:
                list.append(item)

        if len(list) == 0:
            list.append('PropertyPlantAndEquipment')
            # df = self.Financials(list, form_type=form_type)

        df = self.Financials(list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['PropertyPlantAndEquipmentsNet'] = df.sum(axis=1)
        return df

    def PropertyPlantAndEquipmentGrossAndNet(self, form_type="10-K"):
        list = []
        gaaplist = self.gaap_List

        for item in ["PropertyPlantAndEquipmentGross", 'PropertyPlantAndEquipment', "PropertyPlantAndEquipmentNet",
                     "RealEstateInvestmentPropertyAtCost", "RealEstateInvestmentPropertyNet"]:
            if item in gaaplist:
                list.append(item)

        df = self.Financials(list, form_type=form_type)
        df['Ratio'] = df[list[-1]] / df[list[0]]
        df['Ratio'] = df['Ratio'].round(2)
        df.ffill(inplace=True)
        return df

    def Revenues(self, form_type='10-K', show_graph=False):

        gaaplist = self.gaap_List
        synonyms = ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues',
                    'SalesRevenueNet', 'Revenue', 'RevenueFromSaleOfGoods', 'RevenueFromContractsWithCustomers',
                    'NoninterestIncome']
        # SalesRevenueNet
        # SalesRevenueGoodsNet

        list = [item for item in synonyms if item in gaaplist]
        if len(list) == 0:
            list.append("RevenueFromContractWithCustomerIncludingAssessedTax")

        df = self.Financials(list, form_type=form_type)

        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['TotalRevenues'] = df.sum(axis=1)
        df['Repetition'] = df.notnull().sum(axis=1) - 1
        df['TotalRevenues'] = df['TotalRevenues'] / df['Repetition']

        fig = px.bar(df, x=df.index, y=['TotalRevenues'],
                     title=f"{self.company_name}<br><sup>Revenues</sup>",
                     # line_shape="spline",
                     text_auto=True,
                     template="seaborn"
                     )
        fig.update_traces(textangle=0, textposition="outside", cliponaxis=False)
        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          # width=1200,
                          height=500,
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))
        # fig.update_layout({'plot_bgcolor': 'rgba(0,0,0,0)','paper_bgcolor': 'rgba(0,0,0,0)'})

        if show_graph == True:
            fig.show()

        return df['TotalRevenues'], fig

    def NetIncomeLoss(self, form_type='10-K'):

        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ["NetIncomeLoss", 'ProfitLossAttributableToOwnersOfParent',
                    "NetIncomeLossAvailableToCommonStockholdersBasic"]
        list = [item for item in synonyms if item in gaaplist]
        df = self.Financials(list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)

        df['NetIncome'] = df.sum(axis=1)
        return df

    def OperatingIncomeLoss(self, form_type='10-K'):  # should be same as EBIT

        gaaplist = self.gaap_List
        synonyms = ["OperatingIncomeLoss", "IncomeLossFromOperationsBeforeIncomeTaxExpenseBenefit",
                    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"]
        list = [item for item in synonyms if item in gaaplist]
        if len(list) == 0:
            list.extend(
                ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                 "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"])

        df = self.Financials(list, form_type=form_type)
        # This line remove duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)

        df['OperatingIncome'] = df.sum(axis=1)
        return df

    def ProfitMargin(self, form_type='10-K', show_graph=False):
        df = pd.DataFrame()
        df["Revenues"], fig = self.Revenues(form_type=form_type, show_graph=False)
        df["NetIncome"] = self.NetIncomeLoss(form_type=form_type)["NetIncome"]
        df["ProfitMargin"] = df["NetIncome"] / df["Revenues"]

        fig = px.area(df, x=df.index, y=['ProfitMargin'],
                      title=f"{self.company_name}<br><sup>Net Profit Margin</sup>",
                      line_shape="vh",
                      template="seaborn"
                      )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          # width=1200,
                          height=500,
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))
        # fig.update_layout({'plot_bgcolor': 'rgba(0,0,0,0)','paper_bgcolor': 'rgba(0,0,0,0)'})

        # ------------------------------------------------------------------ ADD THE 44SCIENTIFICS LOGO
        fig.add_layout_image(
            dict(
                source="/Users/cheikhcamara/Documents/GitHub/3SIGMA/44 Scientifics logo.jpeg",
                xref="paper", yref="paper",
                x=1, y=1.05,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom",
            )
        )

        if show_graph:
            fig.show()

        return df['ProfitMargin'], fig

    def PriceToEarningsRatio(self, form_type="10-K"):
        df = pd.DataFrame()
        df["NetIncome"] = self.NetIncomeLoss(form_type=form_type)["NetIncome"]
        df["Equity"] = self.Equity(form_type=form_type)["Equity"]
        # df = df.resample('Y').agg({'NetIncome': 'sum', 'Equity': 'last'}).head()
        df["PE"] = df["Equity"] / df["NetIncome"]
        return df

    def EPS(self, form_type="10-K", show_graph=False):

        gaaplist = self.gaap_List

        synonyms = ["EarningsPerShareDiluted"]
        list = [item for item in synonyms if item in gaaplist]
        df = pd.DataFrame()

        if len(list) >= 1:
            df = self.Financials(list, form_type=form_type)
            # This line removes duplicates horizontally across columns
            df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
            df['EarningsPerShare'] = df.sum(axis=1)
        else:
            df = self.NetIncomeLoss(form_type=form_type)
            df["SharesOutstanding"] = self.CommonStockSharesOutstanding(form_type=form_type)
            df["EarningsPerShare"] = df["NetIncome"] / df["SharesOutstanding"]
            df["EarningsPerShare"].fillna(method='ffill', inplace=True)
            df["EarningsPerShare"] = df["EarningsPerShare"].round(2)

        fig = px.area(df, x=df.index, y=['EarningsPerShare'],
                      title=f"{self.company_name}<br><sup>Diluted Earning Per Share (EPS)</sup>",
                      line_shape="vh",
                      template="seaborn"
                      )
        if df['EarningsPerShare'].min() <= 0:
            fig.add_shape(  # add a horizontal "target" line
                type="line", line_color="salmon", line_width=2, opacity=1, line_dash="dot",
                x0=0, x1=1, xref="paper", y0=0.4, y1=0.4, yref="y")
        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          # width=1200,
                          height=500,
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))
        # fig.update_layout({'plot_bgcolor': 'rgba(0,0,0,0)','paper_bgcolor': 'rgba(0,0,0,0)'})
        # ------------------------------------------------------------------ ADD THE 44SCIENTIFICS LOGO
        fig.add_layout_image(
            dict(
                source="/Users/cheikhcamara/Documents/GitHub/3SIGMA/44 Scientifics logo.jpeg",
                xref="paper", yref="paper",
                x=1, y=1.05,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom",
            )
        )

        if show_graph == True:
            fig.show()

        return df['EarningsPerShare'], fig

    def DividendPerShare(self, form_type="10-K", show_graph=False):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        synonyms = ["CommonStockDividendsPerShareCashPaid",
                    "CommonStockDividendsPerShareDeclared"]
        list = [item for item in synonyms if item in gaaplist]
        # if len(list) == 0:
        #     list.append("CommonStockDividendsPerShareDeclared")

        try:
            df = self.Financials(list, form_type=form_type)
            df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
            df['DividendPerShare'] = df.sum(axis=1)
            df['Repetition'] = df.notnull().sum(axis=1) - 1
            df['DividendPerShare'] = df['DividendPerShare'] / df['Repetition']
            return df
        except:
            df = pd.DataFrame()
            return df

    def PaymentsOfDividends(self, form_type="10-K", show_graph=False):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends", 'PaymentsOfOrdinaryDividends',
                    'DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities',
                    'DividendsPaidClassifiedAsFinancingActivities']
        list = [item for item in synonyms if item in gaaplist]

        if len(list) == 0:
            df = pd.DataFrame()
            return df, None
        else:
            df = self.Financials(list, form_type=form_type)
            # This line removes duplicates horizontally across columns
            df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
            df = df.abs()

            percentage_of_missing_data = 0.8
            df = df[df.columns[df.isna().sum() / df.shape[0] < percentage_of_missing_data]]
            df['TotalDividendPaid'] = df.sum(axis=1)
            df['Repetition'] = df.notnull().sum(axis=1) - 1
            df['TotalDividendPaid'] = df['TotalDividendPaid'] / df['Repetition']

            div_df = self.DividendPerShare(form_type=form_type, show_graph=False)
            if div_df.empty:
                div_df["DividendPerShare"] = 0

            result = pd.concat([div_df, df], axis=1)
            # print(result)

            #  ===================================================GRAPH
            fig = go.Figure()

            fig.add_trace(go.Bar(x=df.index, y=df["TotalDividendPaid"],
                                 name="Total Dividend Paid", yaxis='y')
                          )
            fig.add_trace(go.Line(x=result.index, y=result["DividendPerShare"],
                                  name="Dividend per Share", yaxis="y2",
                                  line_shape="hv")
                          )

            # Create axis objects
            fig.update_layout(
                # autosize=False,
                # width=1200,
                height=500,
                margin=dict(l=0, r=0),
                # axis 1
                yaxis=dict(title="Cash From Operating Activities", titlefont=dict(color="#1f77b4"),
                           tickfont=dict(color="#1f77b4"), visible=False),
                # create 2nd y axis
                # create 2nd y axis
                yaxis2=dict(overlaying="y", side="right", position=1, visible=False))

            fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')

            fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')

            fig.update_layout(
                template="seaborn",

                title=f"{self.company_name}<br><sup>Dividend Payments</sup>",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ))

            # fig.update_traces(marker_color='coral')
            # fig.update_layout({'plot_bgcolor': 'rgba(0,0,0,0)','paper_bgcolor': 'rgba(0,0,0,0)'})

            # ------------------------------------------------------------------ ADD THE 44SCIENTIFICS LOGO
            fig.add_layout_image(
                dict(
                    source="/Users/cheikhcamara/Documents/GitHub/3SIGMA/44 Scientifics logo.jpeg",
                    xref="paper", yref="paper",
                    x=1, y=1.05,
                    sizex=0.2, sizey=0.2,
                    xanchor="right", yanchor="bottom",
                )
            )

            if show_graph == True:
                fig.show()

            return result['DividendPerShare'] if (
                    result['DividendPerShare'].count() > result['TotalDividendPaid'].count()) else result[
                'TotalDividendPaid'], fig

    def DividendPayoutRatio(self, form_type="10-K", show_graph=False):
        df = self.DividendPerShare(form_type=form_type, show_graph=False)
        eps_df, fig = self.EPS(form_type=form_type)
        eps = eps_df.to_frame()
        df['EarningsPerShare'] = eps['EarningsPerShare']
        df['DividendPayoutRatio'] = df['DividendPerShare'] / df['EarningsPerShare']

        template = "seaborn"

        fig = px.area(df, x=df.index, y=['DividendPayoutRatio'],
                      title=f"{self.company_name}<br><sup>Dividend Payout Ratio</sup>",
                      line_shape="hv",  # "spline",
                      # width=1200,
                      template=template
                      )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02, x=1,
            xanchor="right",
        ))
        # ------------------------------------------------------------------ ADD THE 44SCIENTIFICS LOGO
        fig.add_layout_image(
            dict(
                source="/Users/cheikhcamara/Documents/GitHub/3SIGMA/44 Scientifics logo.jpeg",
                xref="paper", yref="paper",
                x=0, y=1.05,
                sizex=0.2, sizey=0.2,
                xanchor="left", yanchor="bottom",
            )
        )

        if show_graph == True:
            fig.show()

        return df[["EarningsPerShare", "DividendPerShare", "DividendPayoutRatio"]]

    def DividendYield(self, form_type="10-K", show_graph=False):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = [
            "ShareBasedCompensationArrangementByShareBasedPaymentAwardFairValueAssumptionsExpectedDividendRate"]

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        # This line removes duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df = df.abs()

        percentage_of_missing_data = 0.8
        df = df[df.columns[df.isna().sum() / df.shape[0] <
                           percentage_of_missing_data]]
        df['DividendYield'] = df.sum(axis=1)
        df['Repetition'] = df.notnull().sum(axis=1) - 1
        df['DividendYield'] = df['DividendYield'] / df['Repetition']

        return df['DividendYield']

    # def NextDividendDate(self):
    #     compani = reader.get_quote_yahoo(self.ticker)
    #     next_dividend_date = datetime.fromtimestamp(
    #         compani["dividendDate"][0] if "dividendDate" in compani.columns else 0)
    #     print(next_dividend_date)
    #     day = next_dividend_date.day
    #     month = next_dividend_date.month
    #     year = next_dividend_date.year
    #
    #     return day, month, year

    def PropertyPlantEQuipmentRatio(self, form_type="10-Q", show_graph=False):

        # create an Empty DataFrame object
        df = pd.DataFrame()
        df["PropertyPlantAndEquipmentGross"] = self.PropertyPlantAndEquipmentGross(form_type=form_type)[
            "PropertyPlantAndEquipmentsGross"]
        df["PropertyPlantAndEquipmentNet"] = self.PropertyPlantAndEquipmentNet(form_type=form_type)[
            "PropertyPlantAndEquipmentsNet"]
        df['Ratio'] = df["PropertyPlantAndEquipmentNet"] / df["PropertyPlantAndEquipmentGross"]

        template = "seaborn"

        fig = px.line(df, x=df.index, y=['Ratio'],
                      title=f"{self.company_name}<br><sup>Current State of the company's fixed assets</sup>",
                      line_shape="spline",
                      # width=1200,
                      template=template
                      )
        if df['Ratio'].min() <= 0.4:
            fig.add_shape(  # add a horizontal "target" line
                type="line", line_color="salmon", line_width=2, opacity=1, line_dash="dot",
                x0=0, x1=1, xref="paper", y0=0.4, y1=0.4, yref="y",
            )
        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0), yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))

        if show_graph == True:
            fig.show()

        return df, fig

    def CashFromOperatingActivities(self, form_type="10-K"):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
                    'CashFlowsFromUsedInOperatingActivities', 'NetCashProvidedByUsedInOperatingActivities']
        list = [item for item in synonyms if item in gaaplist]
        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)

        df['CashFromOperatingActivities'] = df.sum(axis=1)

        return df

    def CashCashEquivalents(self, form_type="10-K", show_graph=False):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        synonyms = ['CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
                    'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations',
                    'CashAndCashEquivalents']
        list = [item for item in synonyms if item in gaaplist]
        df = self.Financials(list, form_type=form_type)
        # This line removes duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['CashCashEquivalents'] = df.sum(axis=1)

        template = "seaborn"

        fig = px.bar(df, x=df.index, y=['CashCashEquivalents'],
                     title=f"{self.company_name}<br><sup>Cash & Cash Equivalents</sup>",
                     # line_shape="spline",
                     # width=1200,
                     template=template
                     )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))

        if show_graph == True:
            fig.show()

        return df, fig

    def MarketableSecurities(self, form_type="10-K", show_graph=False):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ['MarketableSecuritiesCurrent', 'ShortTermInvestments']

        list = [item for item in synonyms if item in gaaplist]
        if len(list) == 0:
            df = pd.DataFrame()
        else:
            df = self.Financials(list, form_type=form_type)
        # This line removes duplicates horizontally across columns
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['MarketableAssets'] = df.sum(axis=1)

        df1, figu = self.CashCashEquivalents(form_type=form_type, show_graph=False)
        df['Cash'] = df1['CashCashEquivalents']
        df["Cash and MarketableSecurities"] = df['Cash'] + df['MarketableAssets']
        result = pd.concat([df1, df])

        template = "seaborn"

        fig = px.bar(result, x=result.index, y=['MarketableAssets', 'CashCashEquivalents'],
                     title=f"{self.company_name}<br><sup>Marketable Securities and Cash</sup>",
                     # width=1200,
                     # text_auto='.2f',
                     text_auto=True,
                     # text="nation",
                     template=template
                     )
        fig.update_traces(textangle=0,
                          textposition="outside", cliponaxis=False)
        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))

        if show_graph == True:
            fig.show()

        return result, fig

    def CashFlowFromFinancingActivities(self, form_type='10-K'):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ['NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
                    'CashFlowsFromUsedInFinancingActivities', 'NetCashProvidedByUsedInFinancingActivities']

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)

        df['CashFlowFromFinancingActivities'] = df.sum(axis=1)
        return df

    def CashFlowFromInvestingActivities(self, form_type='10-K'):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        synonyms = ['NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
                    'CashFlowsFromUsedInInvestingActivities', 'NetCashProvidedByUsedInInvestingActivities']

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)

        df['CashFlowFromInvestingActivities'] = df.sum(axis=1)
        return df

    def OperatingCash_VS_Capex(self, form_type="10-K", show_graph=False):
        df = self.CashFromOperatingActivities(form_type=form_type)
        capex = self.Capex(form_type=form_type)
        df['CAPEX'] = capex['CAPEX']

        #  ===================================================GRAPH
        fig = go.Figure()

        fig.add_trace(go.Line(x=df.index, y=df["CashFromOperatingActivities"],
                              name="Cash From Operating Activities", yaxis='y',
                              line_shape="hv",

                              )
                      )

        fig.add_trace(go.Line(x=df.index, y=df["CAPEX"],
                              name="Capex", yaxis="y2",
                              line_shape="hv",

                              )
                      )

        # Create axis objects
        fig.update_layout(
            autosize=False,
            width=1200,
            # height=500,
            yaxis=dict(
                title="Cash From Operating Activities",
                titlefont=dict(color="#1f77b4"),
                tickfont=dict(color="#1f77b4")),

            # create 2nd y axis
            yaxis2=dict(title="Capital Expenditure (CAPEX)", overlaying="y", side="right", position=1))

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')

        fig.update_layout(
            template="seaborn",

            title=f"{self.company_name}<br><sup>Capex vs. Cash From Operating Activities</sup>",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ))

        if show_graph == True:
            fig.show()

        return df, fig

    def IncomeTaxRate(self, form_type="10-K"):
        gaaplist = self.gaap_List

        synonyms = ['EffectiveIncomeTaxRateContinuingOperations']
        list = [item for item in synonyms if item in gaaplist]
        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['IncomeTaxRate'] = df.sum(axis=1)
        return df

    def DepreciationAndAmortization(self, form_type="10-K"):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        synonyms = ['DepreciationAndAmortization', 'DepreciationAndAmortizationExcludingNuclearFuel',
                    "DepreciationDepletionAndAmortization"]

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)

        df['AmortizationAndDepreciation'] = df.sum(axis=1)
        return df

    def DebtInterestRate(self, form_type="10-K"):
        list = []
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ["DebtWeightedAverageInterestRate", "LongtermDebtWeightedAverageInterestRate",
                    'ShortTermDebtWeightedAverageInterestRate']
        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['DebtInterestRate'] = df.sum(axis=1)
        return df

    def InterestExpense(self, form_type="10-K"):
        list = []
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List

        synonyms = ["InterestExpense", "InterestExpenseNetOfHedgeIneffectiveness"]
        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['InterestExpense'] = df.sum(axis=1)
        return df

    def IncomeTaxes(self, form_type='10-K'):
        list = []
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        # IncomeTaxExpenseBenefit
        synonyms = ['IncomeTaxExpenseBenefit',
                    # "IncomeTaxesPaidNet"
                    ]
        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['IncomeTaxes'] = df.sum(axis=1)
        return df

    def CapitalEmployed(self, form_type="10-Q"):
        gaaplist = self.gaap_List

        synonyms = ['Assets', 'LiabilitiesCurrent']

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df["Capital Employed"] = df[df.columns[0]] - df[df.columns[-1]]
        return df

    def DebtRepayment(self, form_type="10-K"):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        synonyms = ["RepaymentsOfLongTermDebt"]

        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['TotalLongTermDebt'] = df.sum(axis=1)

    def LongTermDebt(self, form_type="10-K", show_graph=False):
        # don't show de result of gaaplist on screen, just use the result
        gaaplist = self.gaap_List
        synonyms = ['NoncurrentFinancialLiabilities', 'LongtermBorrowings', 'LongTermDebtNoncurrent', 'LongTermDebt',
                    "LongTermDebtAndCapitalLeaseObligations"]
        # ["DebtInstrumentCarryingAmount"]

        list = [item for item in synonyms if item in gaaplist]

        if len(list) == 0:
            list.extend("OtherLiabilitiesNoncurrent")

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df['TotalLongTermDebt'] = df.sum(axis=1)
        df['Repetition'] = df.notnull().sum(axis=1) - 1
        df['TotalLongTermDebt'] = df['TotalLongTermDebt'] / df['Repetition']

        fig = px.area(df, x=df.index, y=['TotalLongTermDebt'],
                      title=f"{self.company_name}<br><sup>Long-Term Debt</sup>",
                      line_shape="hv",
                      # width=1200,
                      template="seaborn"
                      )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,

        ))

        if show_graph == True:
            fig.show()

        return df, fig

    def ShortTermDebt(self, form_type="10-K", show_graph=False):
        gaaplist = self.gaap_List

        synonyms = ["TradeAndOtherCurrentPayables", "AccountsPayableCurrent", "EmployeeRelatedLiabilitiesCurrent",
                    "CurrentTaxLiabilitiesCurrent", "AccruedIncomeTaxesCurrent", "OtherShorttermProvisions",
                    "LiabilitiesIncludedInDisposalGroupsClassifiedAsHeldForSale",
                    "ContractWithCustomerLiabilityCurrent", "AccountsPayableAndAccruedLiabilitiesCurrent",
                    "AccruedLiabilitiesCurrent", "AccruedRebatesReturnsAndPromotions", "OtherLiabilitiesCurrent"]
        list = [item for item in synonyms if item in gaaplist]

        df = self.Financials(list, form_type=form_type)
        df = df.apply(lambda x: pd.Series(x.unique()), axis=1)
        df["total_to_subtract"] = df.sum(axis=1)
        df2 = self.Financials(["LiabilitiesCurrent"], form_type=form_type)
        df2["ShortTermDebt"] = df2["LiabilitiesCurrent"] - df["total_to_subtract"]
        return df2

    def TotalDebt(self, form_type="10-Q"):
        TotalDebt = self.ShortTermDebt(form_type=form_type, show_graph=False)
        TotalDebt["LongTermDebt"], fig = self.LongTermDebt(
            form_type=form_type, show_graph=False)

        TotalDebt["TotalDebt"] = TotalDebt["LongTermDebt"] + TotalDebt["ShortTermDebt"]

        return TotalDebt[["ShortTermDebt", "LongTermDebt", "TotalDebt"]]

    def ROE(self, form_type="10-Q"):

        match form_type:
            case "10-Q":
                df = self.AssetsLiabilitiesEquity(form_type=form_type)
                df['NetIncome'] = self.NetIncomeLoss(form_type=form_type)['NetIncome']
                df['ROE'] = df['NetIncome'] / df['Equity']
                return df
            case "10-K":
                df = self.AssetsLiabilitiesEquity(form_type="10-Q")
                df['NetIncome'] = self.NetIncomeLoss(form_type=form_type)['NetIncome']
                df['ROE'] = df['NetIncome'] / df['Equity']
                df.dropna(axis=0, inplace=True)
                return df
            case _:
                df = self.AssetsLiabilitiesEquity(form_type="10-Q")
                df['NetIncome'] = self.NetIncomeLoss(form_type=form_type)['NetIncome']
                df['ROE'] = df['NetIncome'] / df['Equity']
                df.dropna(axis=0, inplace=True)
                return df

    def ROCE(self, form_type='10-Q', show_graph=False):

        ebit = self.OperatingIncomeLoss(form_type="10-K")
        capitalEmployed = self.CapitalEmployed(form_type="10-Q")
        df = pd.concat([capitalEmployed["Capital Employed"], ebit["OperatingIncome"]], axis=1)
        df.dropna(axis=0, inplace=True)
        df['ROCE'] = df['OperatingIncome'] / df['Capital Employed']

        template = "seaborn"

        fig = px.area(df, x=df.index, y=['ROCE'],
                      title=f"{self.company_name}<br><sup>Return on Capital Employed (ROCE)</sup>",
                      line_shape="vh",
                      template=template
                      )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0), yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ))
        if show_graph == True:
            fig.show()

        return df, fig

    def EBITDA(self, form_type="10-Q", show_graph=False):
        df = self.OperatingIncomeLoss(form_type=form_type)
        df2 = self.DepreciationAndAmortization(form_type=form_type)
        df["Amortization"] = df2["AmortizationAndDepreciation"]
        df["EBITDA"] = df["OperatingIncomeLoss"] + df["Amortization"]

        # PLOTLY FIGURE
        template = "seaborn"

        fig = px.bar(df, x=df.index, y=['EBITDA'],
                     title=f"{self.company_name}<br><sup>EBITDA</sup>",
                     # line_shape="spline",
                     template=template,
                     # width=1200
                     )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ))

        if show_graph == True:
            fig.show()

        figplot = plot(fig, output_type="div")
        return df, figplot

    def EBIT(self, form_type="10-K"):
        net_income = self.NetIncomeLoss(form_type=form_type)
        interest_expense = self.InterestExpense(form_type=form_type)
        income_tax = self.IncomeTaxes(form_type=form_type)
        df = pd.concat(
            [net_income["NetIncome"], interest_expense["InterestExpense"], income_tax["IncomeTaxes"]], axis=1)

        df["EBIT"] = df.sum(axis=1)
        return df

    def WorkingCapital(self, form_type="10-Q", show_graph=False):
        list = []
        gaaplist = self.gaap_List

        for item in ["AssetsCurrent", 'LiabilitiesCurrent']:
            if item in gaaplist:
                list.append(item)

        df = self.Financials(list, form_type=form_type)
        # if form_type == "10-K":
        #    df = df.resample('BY').last()

        df["Working Capital"] = df["AssetsCurrent"] - df["LiabilitiesCurrent"]

        # PLOTLY FIGURE
        template = "seaborn"

        fig = px.line(df, x=df.index, y=['Working Capital'],
                      title=f"{self.company_name}<br><sup>Working Capital - Quarterely</sup>",
                      line_shape="spline",
                      template=template,
                      width=1200
                      )

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_layout(margin=dict(l=0, r=0),
                          yaxis_title=None, xaxis_title=None)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ))

        if show_graph == True:
            fig.show()

        figplot = plot(fig, output_type="div")
        return df, figplot

    def FreeCashFlow(self, form_type='10-K', show_graph=False):
        df = self.CashFromOperatingActivities(form_type=form_type)
        df1 = self.Capex(form_type=form_type)
        df["CAPEX"] = df1['CAPEX']
        df["FreeCashFlow"] = df["CashFromOperatingActivities"] - df["CAPEX"]
        df['SharesOutstanding'] = self.CommonStockSharesOutstanding(form_type=form_type)
        df['SharesOutstanding'].ffill(inplace=True)
        df["FreeCashFowPerShare"] = df["FreeCashFlow"] / df['SharesOutstanding']

        #  ===================================================GRAPH
        fig = go.Figure()

        fig.add_trace(go.Bar(x=df.index, y=df["FreeCashFowPerShare"], name="Free Cashflow / Share", yaxis='y')
                      )

        fig.add_trace(go.Line(x=df.index, y=df["FreeCashFlow"],
                              name="Free Cash Flow", yaxis="y2",
                              line_shape="hv")
                      )

        # Create axis objects
        fig.update_layout(
            # autosize=False,
            width=1400,
            height=500,
            margin=dict(l=0, r=0),
            # axis 1
            yaxis=dict(titlefont=dict(color="#1f77b4"), tickfont=dict(color="#1f77b4"), visible=False),
            # create 2nd y axis
            yaxis2=dict(overlaying="y", side="right", position=1, visible=False))

        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')

        fig.update_layout(
            template="seaborn",

            title=f"{self.company_name}<br><sup>Free Cash Flow</sup>",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ))

        if show_graph == True:
            fig.show()

        figplot = plot(fig, output_type="div")
        return df, figplot

    def EntrepriseValue(self, form_type='10-K', show_graph=False):
        list = []
        gaaplist = self.gaap_List

        for item in ["DepreciationDepletionAndAmortization", 'InterestExpense', 'NetIncomeLoss',
                     'IncomeTaxExpenseBenefit', 'InterestIncomeExpenseNet']:
            if item in gaaplist:
                list.append(item)

        df = self.Financials(list, form_type=form_type)
        df['EBITDA'] = df.sum(axis=1)
        return df
