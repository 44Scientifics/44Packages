import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from functools import reduce
from typing import List, Optional, Dict, Any
from FortyFour.Finance.utils import get_all_cik, request_company_filing # Assuming these are correctly imported

class CompanyV2:
    """
    Refactored Company class for fetching and analyzing financial data from SEC filings.
    """

    GAAP_SYNONYMS: Dict[str, List[str]] = {
        "Assets": ["Assets"],
        "AssetsCurrent": ["AssetsCurrent"],
        "Capex": [
            'PaymentsToAcquirePropertyPlantAndEquipment', "PaymentsToAcquireOtherPropertyPlantAndEquipment",
            'PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
            "PaymentsToAcquireRealEstateHeldForInvestment", "PaymentsToDevelopRealEstateAssets",
            "PaymentsForCapitalImprovements", 'PaymentsToAcquireAndDevelopRealEstate',
            "PaymentsToAcquireRealEstate", "PaymentsToAcquireCommercialRealEstate",
            "PaymentsToAcquireProductiveAssets",
            "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
            "PurchaseOfPropertyPlantAndEquipmentAndIntangibleAssets", 'PurchasesOfPropertyAndEquipmentAndIntangibleAssets',
        ],
        "CashCashEquivalents": [
            'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
            'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations',
            'CashAndCashEquivalentsAtCarryingValue', 'CashAndCashEquivalents' # Added common variations
        ],
        "CashFromOperatingActivities": [
            'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
            'NetCashProvidedByUsedInOperatingActivities', 'CashFlowsFromUsedInOperatingActivities'
        ],
        "CashFlowFromFinancingActivities": [
            'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
            'NetCashProvidedByUsedInFinancingActivities', 'CashFlowsFromUsedInFinancingActivities'
        ],
        "CashFlowFromInvestingActivities": [
            'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
            'NetCashProvidedByUsedInInvestingActivities', 'CashFlowsFromUsedInInvestingActivities'
        ],
        "CommonStockSharesOutstanding": [
            'WeightedAverageNumberOfDilutedSharesOutstanding', 'CommonStockSharesIssued',
            'EntityCommonStockSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingDiluted',
            'WeightedAverageSharesOutstandingDiluted', 'CommonStockSharesOutstanding'
        ],
        "CostOfGoodsAndServicesSold": ['CostOfGoodsAndServicesSold', 'CostOfRevenue'],
        "DepreciationAndAmortization": [
            'DepreciationAndAmortization', 'DepreciationDepletionAndAmortization',
            'DepreciationAndAmortizationExcludingNuclearFuel'
        ],
        "EarningsPerShareDiluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
        "EffectiveIncomeTaxRateContinuingOperations": ['EffectiveIncomeTaxRateContinuingOperations'],
        "EntityPublicFloat": ["EntityPublicFloat"],
        "Equity": [
            'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            'StockholdersEquity', 'EquityAttributableToOwnersOfParent', 'Equity'
        ],
        "IncomeTaxExpenseBenefit": ['IncomeTaxExpenseBenefit', "IncomeTaxesPaidNet"],
        "InterestExpense": ["InterestExpense", "InterestExpenseNet", "InterestExpenseNetOfHedgeIneffectiveness"],
        "LiabilitiesCurrent": ['LiabilitiesCurrent'],
        "LongTermDebt": [
            'LongTermDebtNoncurrent', 'LongTermDebt', 'LongtermBorrowings',
            "LongTermDebtAndCapitalLeaseObligations", "OtherLiabilitiesNoncurrent",
            'NoncurrentFinancialLiabilities'
        ],
        "MarketableSecuritiesCurrent": ['MarketableSecuritiesCurrent', 'ShortTermInvestments'],
        "NetIncomeLoss": [
            "NetIncomeLoss", 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic',
            'ProfitLossAttributableToOwnersOfParent'
        ],
        "OperatingIncomeLoss": [
            "OperatingIncomeLoss",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromOperationsBeforeIncomeTaxExpenseBenefit"
        ],
        "PropertyPlantAndEquipmentGross": [
            "PropertyPlantAndEquipmentGross", "RealEstateInvestmentPropertyAtCost",
            "GrossInvestmentInRealEstateAssets", 'PropertyPlantAndEquipment' # Note: 'PropertyPlantAndEquipment' can be ambiguous (net or gross)
        ],
        "PropertyPlantAndEquipmentNet": [
            "PropertyPlantAndEquipmentNet", "NetInvestmentInRealEstateAssets",
            'RealEstateInvestmentPropertyNet', 'PropertyPlantAndEquipment'
        ],
        "Revenues": [
            'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet',
            'Revenue', 'RevenueFromSaleOfGoods', 'RevenueFromContractsWithCustomers', 'NoninterestIncome'
        ],
        "ShortTermPayablesForDebtCalc": [ # Specific group for ShortTermDebt calculation
            "TradeAndOtherCurrentPayables", "AccountsPayableCurrent", "EmployeeRelatedLiabilitiesCurrent",
            "CurrentTaxLiabilitiesCurrent", "AccruedIncomeTaxesCurrent", "OtherShorttermProvisions",
            "LiabilitiesIncludedInDisposalGroupsClassifiedAsHeldForSale",
            "ContractWithCustomerLiabilityCurrent", "AccountsPayableAndAccruedLiabilitiesCurrent",
            "AccruedLiabilitiesCurrent", "AccruedRebatesReturnsAndPromotions", "OtherLiabilitiesCurrent"
        ],
        # Add other concepts and their synonyms here
    }


    def __init__(self, ticker: str, cik: Optional[str] = None, logo_path: Optional[str] = None):
        self.ticker = str.upper(ticker)
        self.cik = cik
        self.company_name: str = "Unknown Company"
        self.GAAP_NORM: Optional[str] = None
        self._facts: Dict[str, Any] = {}
        self.available_gaap_list: List[str] = []
        self.logo_path = logo_path # Path for logo in plots

        if self.cik is None:
            try:
                all_ciks_df = get_all_cik()
                if 'ticker' not in all_ciks_df.columns or 'cik' not in all_ciks_df.columns:
                    raise ValueError("Required 'ticker' or 'cik' column missing in CIK data.")
                
                company_cik_series = all_ciks_df.loc[all_ciks_df['ticker'] == self.ticker, 'cik']
                if not company_cik_series.empty:
                    self.cik = str(company_cik_series.iloc[0]).zfill(10) # Ensure CIK is 10 digits, zero-padded
                else:
                    raise ValueError(f"CIK not found for ticker: {self.ticker}")
            except Exception as e:
                logging.error(f"Error resolving CIK for {self.ticker}: {e}")
                raise

        if not self.cik:
            raise ValueError(f"CIK could not be determined for ticker: {self.ticker}")

        try:
            self.response = request_company_filing(self.cik)
            if not self.response or "facts" not in self.response or not isinstance(self.response["facts"], dict):
                raise ValueError(f"Invalid or missing 'facts' in company filings for CIK: {self.cik}")
            self._facts = self.response["facts"]
        except Exception as e:
            logging.error(f"Failed to fetch or parse company filings for CIK {self.cik}: {e}")
            raise

        self.company_name = self.response.get('entityName', self.company_name)

        # Determine accounting norm (e.g., us-gaap, ifrs-full)
        # Prefer us-gaap, then ifrs-full, then the last one found, then dei as last resort
        preferred_norms = ["us-gaap", "ifrs-full"]
        available_norms_in_facts = [norm for norm in self._facts.keys() if norm not in ["srt", "invest", "dei"]]

        for p_norm in preferred_norms:
            if p_norm in available_norms_in_facts:
                self.GAAP_NORM = p_norm
                break
        
        if not self.GAAP_NORM and available_norms_in_facts:
            self.GAAP_NORM = available_norms_in_facts[-1] # Fallback to the last one
        elif not self.GAAP_NORM and "dei" in self._facts:
            self.GAAP_NORM = "dei" # Last resort
            logging.warning(f"No standard accounting norms found for {self.ticker}. Using 'dei'. Data quality may vary.")
        
        if not self.GAAP_NORM or self.GAAP_NORM not in self._facts:
            raise ValueError(f"No suitable accounting norms or 'dei' found in facts for {self.ticker}.")

        logging.info(f"Using Accounting Norm for {self.ticker} ({self.company_name}): {self.GAAP_NORM}")
        self.available_gaap_list = list(self._facts[self.GAAP_NORM].keys()) if self.GAAP_NORM in self._facts else []
        if self.GAAP_NORM == "dei" and not self.available_gaap_list: # If DEI was chosen and it's empty
             self.available_gaap_list = list(self._facts.get("dei", {}).keys())


    def _get_raw_data_for_item(self, gaap_item: str) -> pd.DataFrame:
        """
        Internal helper to fetch raw data for a single GAAP item.
        It tries self.GAAP_NORM first, then 'dei' as a fallback if the item is not in self.GAAP_NORM.
        """
        data_sources_to_try = [self.GAAP_NORM]
        if "dei" not in data_sources_to_try: # Add 'dei' if not already the primary norm
            data_sources_to_try.append("dei")

        for norm in data_sources_to_try:
            if not norm or norm not in self._facts: continue

            if gaap_item in self._facts[norm]:
                try:
                    item_data = self._facts[norm][gaap_item]
                    if 'units' not in item_data or not isinstance(item_data['units'], dict) or not item_data['units']:
                        continue # No units data

                    # Prefer USD or shares, then the first unit found. Original took last.
                    unit_key = None
                    if "USD" in item_data['units']: unit_key = "USD"
                    elif "shares" in item_data['units']: unit_key = "shares"
                    elif item_data['units']: unit_key = list(item_data['units'].keys())[0]

                    if unit_key and item_data['units'][unit_key]:
                        records = item_data['units'][unit_key]
                        df = pd.DataFrame.from_records(records)
                        # Select essential columns. 'filed' is crucial for quarterly/annual distinction.
                        cols_to_keep = ['val', 'end', 'form', 'filed', 'frame']
                        df = df[[col for col in cols_to_keep if col in df.columns]]
                        # Ensure 'val' exists and drop rows where it's NaN
                        if 'val' in df.columns:
                            return df.dropna(subset=['val'])
                        return pd.DataFrame() # val column missing
                except Exception as e:
                    logging.debug(f"Error processing {gaap_item} under {norm} for {self.ticker}: {e}")
        return pd.DataFrame()

    def _filter_by_form_type(self, df: pd.DataFrame, form_type: Optional[str]) -> pd.DataFrame:
        if df.empty or form_type is None:
            return df.drop(columns=['form', 'frame', 'filed'], errors='ignore')

        # Ensure 'filed' is datetime for sorting and 'form' is uppercase
        if 'filed' in df.columns:
            df['filed'] = pd.to_datetime(df['filed'], errors='coerce')
        if 'form' in df.columns:
            df['form'] = df['form'].astype(str).str.upper()

        # Drop duplicates: prefer later filings for the same period ('end' date and 'form')
        # This helps get the most up-to-date version (e.g. 10-K/A over 10-K)
        if 'filed' in df.columns and 'end' in df.columns and 'form' in df.columns:
            df = df.sort_values('filed', ascending=False).drop_duplicates(subset=['end', 'form'], keep='first')
        elif 'end' in df.columns and 'form' in df.columns: # Fallback if 'filed' is missing
             df = df.drop_duplicates(subset=['end', 'form'], keep='last')


        # Filter by form type (10-K, 10-Q, etc.)
        # The 'frame' column (e.g., CY2023Q1, CY2023) can also indicate periodicity.
        # Prioritize 'form' column, then 'frame'.
        if "form" in df.columns:
            if form_type == "10-Q":
                df = df[df["form"] == "10-Q"]
            elif form_type in ["10-K", "20-F", "40-F"]: # Annual reports (20-F, 40-F for foreign issuers)
                df = df[df["form"].isin(["10-K", "20-F", "40-F", "10-K/A", "20-F/A", "40-F/A"])] # Include amendments
        elif "frame" in df.columns: # Fallback to 'frame' if 'form' column is not definitive
            if form_type == "10-Q":
                df = df[df["frame"].str.contains('Q', na=False)]
            elif form_type in ["10-K", "20-F", "40-F"]:
                df = df[~df["frame"].str.contains('Q', na=False)]
        
        return df.drop(columns=['form', 'frame', 'filed'], errors='ignore')

    def get_financial_data(self,
                           gaap_concepts: List[str],
                           form_type: Optional[str] = None,
                           custom_gaap_items: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetches, processes, and merges financial data for specified GAAP concepts or custom GAAP items.
        - gaap_concepts: List of conceptual names (e.g., "Revenues"). Synonyms will be looked up.
        - form_type: Filters data by SEC form type (e.g., "10-K", "10-Q").
        - custom_gaap_items: List of specific GAAP tags to fetch directly without synonym lookup.
        """
        all_final_dfs_to_merge: List[pd.DataFrame] = []

        # Consolidate all unique GAAP items to fetch (from concepts and custom_items)
        actual_gaap_items_to_fetch_map: Dict[str, str] = {} # Maps item_name to its concept_name or itself
        
        for concept_name in gaap_concepts:
            synonyms = self.GAAP_SYNONYMS.get(concept_name, [concept_name])
            for syn in synonyms:
                # Only consider items potentially available (in primary norm or dei)
                # This check is loose; _get_raw_data_for_item will confirm existence.
                if syn in self.available_gaap_list or syn in self._facts.get("dei", {}):
                    actual_gaap_items_to_fetch_map[syn] = concept_name
        
        if custom_gaap_items:
            for custom_item in custom_gaap_items:
                 if custom_item in self.available_gaap_list or custom_item in self._facts.get("dei", {}):
                    actual_gaap_items_to_fetch_map[custom_item] = custom_item # Maps to itself

        # Fetch and filter raw data for each unique item
        processed_item_dfs: Dict[str, pd.DataFrame] = {} # Stores DFs for individual GAAP items (synonyms)
        for item_name, _ in actual_gaap_items_to_fetch_map.items():
            if item_name in processed_item_dfs: continue

            df_raw = self._get_raw_data_for_item(item_name)
            if df_raw.empty: continue

            df_filtered = self._filter_by_form_type(df_raw.copy(), form_type)
            if df_filtered.empty: continue
            
            df_prepared = df_filtered.rename(columns={'val': item_name, 'end': 'Date'})
            df_prepared['Date'] = pd.to_datetime(df_prepared['Date'])
            
            if item_name in df_prepared.columns and 'Date' in df_prepared.columns:
                # Keep only Date and item_name, drop duplicates on Date, set index
                df_final_item = df_prepared[['Date', item_name]].drop_duplicates(subset=['Date'], keep='first').set_index('Date')
                processed_item_dfs[item_name] = df_final_item

        # For each requested concept, combine its synonym DFs into a single column for that concept
        for concept_name in gaap_concepts:
            synonyms_for_concept = self.GAAP_SYNONYMS.get(concept_name, [concept_name])
            
            # Get DFs for these synonyms that were successfully processed
            dfs_for_current_concept = [processed_item_dfs[syn] for syn in synonyms_for_concept if syn in processed_item_dfs and not processed_item_dfs[syn].empty]

            if not dfs_for_current_concept:
                logging.debug(f"No data found for concept '{concept_name}' or its synonyms after processing.")
                continue

            # Merge all synonym DFs for this concept (outer join on Date index)
            # Then coalesce them into a single column named `concept_name`
            if len(dfs_for_current_concept) == 1:
                # If only one synonym DF, rename its column to the concept name
                concept_df = dfs_for_current_concept[0].copy()
                concept_df.rename(columns={concept_df.columns[0]: concept_name}, inplace=True)
            else:
                # Merge all DFs for the synonyms of this concept
                merged_synonyms_df = reduce(lambda left, right: pd.merge(left, right, on='Date', how='outer'), dfs_for_current_concept)
                
                # Coalesce into the concept_name column
                # Start with the first available synonym column as the base
                base_col_for_coalesce = None
                for syn_col in [s for s in synonyms_for_concept if s in merged_synonyms_df.columns]: # Iterate over available synonym columns
                    if base_col_for_coalesce is None:
                        base_col_for_coalesce = syn_col
                        merged_synonyms_df[concept_name] = merged_synonyms_df[base_col_for_coalesce]
                    else:
                        merged_synonyms_df[concept_name] = merged_synonyms_df[concept_name].combine_first(merged_synonyms_df[syn_col])
                
                if concept_name in merged_synonyms_df:
                    concept_df = merged_synonyms_df[[concept_name]]
                else: # Should not happen if dfs_for_current_concept was not empty
                    logging.warning(f"Failed to create coalesced column for concept '{concept_name}'.")
                    continue
            
            all_final_dfs_to_merge.append(concept_df)

        # Add custom_gaap_items that are not part of any concept's synonyms (if any were successfully processed)
        if custom_gaap_items:
            for custom_item in custom_gaap_items:
                # Check if this custom_item was already included via a concept
                is_part_of_concept = any(custom_item in self.GAAP_SYNONYMS.get(c, []) for c in gaap_concepts)
                if not is_part_of_concept and custom_item in processed_item_dfs:
                    all_final_dfs_to_merge.append(processed_item_dfs[custom_item]) # Already has custom_item as column name

        if not all_final_dfs_to_merge:
            return pd.DataFrame().set_index(pd.Index([], name='Date')) # Return empty DataFrame with Date index

        # Final merge of all concept/custom_item DFs
        # Use a loop for merging to handle cases where a df might be empty or only has index
        final_df = all_final_dfs_to_merge[0]
        for i in range(1, len(all_final_dfs_to_merge)):
            final_df = pd.merge(final_df, all_final_dfs_to_merge[i], on='Date', how='outer')
        
        final_df.sort_index(inplace=True)
        return final_df

    def _create_plot(self, df: pd.DataFrame, y_columns: List[str], title_suffix: str,
                     plot_type: str = "bar", line_shape: str = "spline",
                     text_auto: Any = True, # Can be bool or '.2s' etc.
                     yaxis_title: Optional[str] = None,
                     barmode: Optional[str] = None) -> go.Figure: # Added barmode for stacked/grouped bars
        
        # Check if all y_columns exist and have data
        valid_y_columns = [col for col in y_columns if col in df.columns and not df[col].dropna().empty]
        
        if not valid_y_columns:
            fig = go.Figure()
            fig.update_layout(title_text=f"{self.company_name}<br><sup>No data for {title_suffix}</sup>", template="seaborn")
            return fig

        if plot_type == "bar":
            fig = px.bar(df, x=df.index, y=valid_y_columns, text_auto=text_auto, barmode=barmode)
        elif plot_type == "area":
            fig = px.area(df, x=df.index, y=valid_y_columns, line_shape=line_shape)
        elif plot_type == "line":
            fig = px.line(df, x=df.index, y=valid_y_columns, line_shape=line_shape)
        else:
            raise ValueError(f"Unsupported plot_type: {plot_type}")

        fig.update_layout(
            title_text=f"{self.company_name}<br><sup>{title_suffix}</sup>",
            template="seaborn",
            margin=dict(l=30, r=30, t=60, b=30),
            yaxis_title=yaxis_title,
            xaxis_title=None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black', type='category') # type='category' for distinct bars
        fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')
        
        if text_auto and plot_type == "bar":
             fig.update_traces(textangle=0, textposition="outside", cliponaxis=False)

        if self.logo_path:
            try:
                fig.add_layout_image(
                    dict(source=self.logo_path, xref="paper", yref="paper",
                         x=1, y=1.05, sizex=0.12, sizey=0.12,
                         xanchor="right", yanchor="bottom"))
            except Exception as e:
                logging.warning(f"Could not add logo from {self.logo_path}: {e}")
        return fig

    # --- Example Refactored Financial Metric Methods ---

    def Revenues(self, form_type: str = '10-K', show_graph: bool = False) -> tuple[pd.DataFrame, go.Figure]:
        concept = "Revenues"
        df_financials = self.get_financial_data(gaap_concepts=[concept], form_type=form_type)
        
        fig = self._create_plot(df_financials, y_columns=[concept], title_suffix=concept, plot_type="bar")
        
        if show_graph:
            fig.show()
        
        return df_financials[[concept]] if concept in df_financials else pd.DataFrame(index=df_financials.index), fig

    def NetIncomeLoss(self, form_type: str = '10-K', show_graph: bool = False) -> tuple[pd.DataFrame, go.Figure]:
        concept = "NetIncomeLoss"
        df_financials = self.get_financial_data(gaap_concepts=[concept], form_type=form_type)
        
        # You might want a different plot type or customization for NetIncomeLoss
        fig = self._create_plot(df_financials, y_columns=[concept], title_suffix="Net Income (Loss)", plot_type="bar")
        
        if show_graph:
            fig.show()
            
        return df_financials[[concept]] if concept in df_financials else pd.DataFrame(index=df_financials.index), fig

    def CommonStockSharesOutstanding(self, form_type: str = "10-K", show_graph: bool = False) -> tuple[pd.DataFrame, go.Figure]:
        concept = "CommonStockSharesOutstanding"
        df_financials = self.get_financial_data(gaap_concepts=[concept], form_type=form_type)
        
        fig = self._create_plot(df_financials, y_columns=[concept], title_suffix="Common Stock Shares Outstanding", plot_type="line")

        if show_graph:
            fig.show()
            
        return df_financials[[concept]] if concept in df_financials else pd.DataFrame(index=df_financials.index), fig
        
    def EPS(self, form_type: str = "10-K", show_graph: bool = False) -> tuple[pd.DataFrame, go.Figure]:
        eps_concept = "EarningsPerShareDiluted"
        net_income_concept = "NetIncomeLoss"
        shares_concept = "CommonStockSharesOutstanding"

        df_eps = self.get_financial_data(gaap_concepts=[eps_concept], form_type=form_type)

        final_eps_col_name = "EarningsPerShare" # Standardized output column name

        if eps_concept in df_eps.columns and not df_eps[eps_concept].dropna().empty:
            df_result = df_eps[[eps_concept]].rename(columns={eps_concept: final_eps_col_name})
        else:
            logging.info(f"{eps_concept} not found directly, calculating from NetIncome and Shares.")
            df_components = self.get_financial_data(gaap_concepts=[net_income_concept, shares_concept], form_type=form_type)
            df_result = pd.DataFrame(index=df_components.index)
            if net_income_concept in df_components and shares_concept in df_components:
                # Ensure no division by zero or NaN shares
                shares = df_components[shares_concept].replace(0, pd.NA)
                df_result[final_eps_col_name] = (df_components[net_income_concept] / shares).round(2)
                df_result[final_eps_col_name].ffill(inplace=True) # Forward fill, as in original
            else:
                df_result[final_eps_col_name] = pd.NA


        fig = self._create_plot(df_result, y_columns=[final_eps_col_name],
                                title_suffix="Diluted Earnings Per Share (EPS)",
                                plot_type="area", line_shape="vh") # vh for step-like appearance

        # Add zero line if min EPS is non-positive
        if final_eps_col_name in df_result and not df_result[final_eps_col_name].empty:
            min_eps = df_result[final_eps_col_name].min()
            if pd.notna(min_eps) and min_eps <= 0:
                 fig.add_hline(y=0, line_dash="dot", line_color="salmon", line_width=2, opacity=0.7)
        
        if show_graph:
            fig.show()
            
        return df_result[[final_eps_col_name]] if final_eps_col_name in df_result else pd.DataFrame(index=df_result.index), fig

    def ProfitMargin(self, form_type:str = '10-K', show_graph:bool = False) -> tuple[pd.DataFrame, go.Figure]:
        concepts = ["Revenues", "NetIncomeLoss"]
        df_data = self.get_financial_data(gaap_concepts=concepts, form_type=form_type)

        result_df = pd.DataFrame(index=df_data.index)
        margin_col = "ProfitMargin"

        if "Revenues" in df_data.columns and "NetIncomeLoss" in df_data.columns:
            # Avoid division by zero or NaN revenues
            revenues = df_data["Revenues"].replace(0, pd.NA)
            result_df[margin_col] = (df_data["NetIncomeLoss"] / revenues)
        else:
            result_df[margin_col] = pd.NA
            logging.warning("Revenues or NetIncomeLoss data not found for ProfitMargin calculation.")

        fig = self._create_plot(result_df, y_columns=[margin_col],
                                title_suffix="Net Profit Margin",
                                plot_type="area", line_shape="vh")
        fig.update_yaxes(tickformat=".2%") # Format y-axis as percentage

        if show_graph:
            fig.show()
        
        return result_df[[margin_col]] if margin_col in result_df else pd.DataFrame(index=result_df.index), fig

    # --- Compounding Annual Growth Rate (CAGR) ---
    # This method is largely independent as it operates on an input DataFrame.
    # It can be copied with minor adjustments for self.company_name.
    def compounding_annual_growth_rate(self, df: pd.DataFrame, nb_years: int, inline_graph: bool = False) -> go.Figure:
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        fig_title_text = f"{self.company_name}<br><sup>No Data for {nb_years}-Years CAGR</sup>"
        cagr_value = 0
        delta_ref = 0
        gauge_axis_range = [0, 20] # Default for no data
        gauge_steps = []

        if len(df.index) >= (nb_years + 1) and not df.empty and not df.iloc[:, 0].empty:
            try:
                # Ensure we are using numeric data from the first column
                numeric_series = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna()
                if len(numeric_series) >= (nb_years + 1):
                    ending_value = numeric_series.iloc[-1]
                    beginning_value = numeric_series.iloc[-nb_years - 1]

                    if beginning_value != 0 and pd.notna(beginning_value) and pd.notna(ending_value):
                        # Handle negative beginning values carefully if growth is expected
                        if beginning_value < 0 and ending_value > 0: # Growth from negative to positive
                             cagr_value = float('inf') # Or handle as special case
                        elif beginning_value < 0 and ending_value < 0: # Both negative
                            # CAGR formula might be misleading. Consider absolute change or skip.
                            # For now, apply formula, but be wary of interpretation.
                            cagr_value = round(((ending_value / beginning_value) ** (1 / nb_years) - 1) * 100, 1) if nb_years > 0 else 0
                        else: # Standard case
                            cagr_value = round(((ending_value / beginning_value) ** (1 / nb_years) - 1) * 100, 1) if nb_years > 0 else 0
                        
                        fig_title_text = f"{self.company_name}<br><sup>{nb_years}-Years CAGR</sup>"
                        delta_ref = 10  # Example reference for delta
                        gauge_axis_range = [-50, 50] # Wider range for actual CAGR
                        gauge_steps = [
                            {'range': [-50, 0], 'color': "pink"},
                            {'range': [0, 10], 'color': "lightgray"},
                            {'range': [10, 25], 'color': "lightcyan"},
                            {'range': [25, 50], 'color': "lightgreen"}
                        ]
                    else:
                        logging.warning("CAGR calculation: Beginning value is zero or NaN, or ending value is NaN.")
                else:
                    logging.warning(f"Not enough numeric data points for {nb_years}-year CAGR after cleaning.")
            except Exception as e:
                logging.warning(f'The function compounding_annual_growth_rate() encountered an exception: {e}')
                cagr_value = 0 # Reset on error
        else:
            logging.info(f"Not enough data points for {nb_years}-year CAGR.")


        fig = go.Figure(go.Indicator(
            domain={'x': [0, 1], 'y': [0, 1]},
            value=cagr_value,
            mode="gauge+number+delta",
            title={'text': fig_title_text, 'font': {'size': 16}},
            delta={'reference': delta_ref, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
            gauge={
                'axis': {'range': gauge_axis_range, 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "darkblue"},
                'steps': gauge_steps,
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': delta_ref if delta_ref !=0 else 5} # Threshold at delta_ref
            }))
        
        fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))

        if inline_graph:
            fig.show()
        return fig

    # ... (Continue refactoring other methods like AssetsLiabilitiesEquity, Capex, etc., using get_financial_data and _create_plot)
    # For example:
    # def AssetsLiabilitiesEquity(self, form_type="10-Q", show_graph=False):
    #     concepts = ["Assets", "Equity"]
    #     df_data = self.get_financial_data(gaap_concepts=concepts, form_type=form_type)
    #     # ... rest of the logic to calculate Liabilities, Ratio, and call _create_plot ...
    #     return df_result, fig


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Example: Replace with a ticker and CIK you have data for, or ensure get_all_cik() works.
    # You might need to provide a logo_path if you want logos in plots.
    # logo_path_example = "/path/to/your/logo.png" 
    
    try:
        # Ensure get_all_cik() returns a DataFrame with 'ticker' and 'cik' columns
        # and request_company_filing(cik) returns the expected JSON structure.
        
        # Example with Apple (CIK: 0000320193)
        # company = CompanyV2(ticker="AAPL", cik="0000320193") # Or let CIK be looked up
        company = CompanyV2(ticker="MSFT") # Microsoft, CIK will be looked up

        print(f"Company Name: {company.company_name}, CIK: {company.cik}, GAAP Norm: {company.GAAP_NORM}")

        # Test a few methods
        df_revenues, fig_revenues = company.Revenues(form_type="10-K", show_graph=False)
        print("\nRevenues (10-K):\n", df_revenues.tail())
        # fig_revenues.show() # Uncomment to display plot

        df_eps, fig_eps = company.EPS(form_type="10-K", show_graph=False)
        print("\nEPS (10-K):\n", df_eps.tail())
        # fig_eps.show() # Uncomment to display plot
        
        df_profit_margin, fig_pm = company.ProfitMargin(form_type="10-K", show_graph=False)
        print("\nProfit Margin (10-K):\n", df_profit_margin.tail())

        # Test CAGR on Revenues (ensure df_revenues has data)
        if not df_revenues.empty and "Revenues" in df_revenues.columns and not df_revenues["Revenues"].dropna().empty:
            cagr_fig = company.compounding_annual_growth_rate(df_revenues[["Revenues"]], nb_years=5, inline_graph=False)
            print("\nCAGR Figure created.")
            # cagr_fig.show()
        else:
            print("\nSkipping CAGR test due to empty revenues data.")

    except ValueError as ve:
        print(f"ValueError during CompanyV2 initialization or usage: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

""" ```

**Key Changes and How to Proceed:**

1.  **`GAAP_SYNONYMS`**: This class attribute centralizes all known GAAP tags for common financial concepts. You'll need to ensure this dictionary is comprehensive for all the metrics your class supports.
2.  **`__init__`**:
    *   Improved CIK lookup with better error handling.
    *   More robust determination of `GAAP_NORM`, preferring `us-gaap` or `ifrs-full`.
    *   Stores `self._facts` for internal use.
3.  **`_get_raw_data_for_item`**: Fetches data for a single, specific GAAP item, trying `self.GAAP_NORM` then `dei`.
4.  **`_filter_by_form_type`**: Applies filtering based on `form_type` (e.g., "10-K", "10-Q") and handles deduplication by preferring later filings.
5.  **`get_financial_data`**: This is the new core data retrieval method.
    *   It takes a list of `gaap_concepts` (e.g., "Revenues", "NetIncomeLoss").
    *   For each concept, it looks up synonyms in `GAAP_SYNONYMS`.
    *   It fetches raw data for all relevant synonyms using `_get_raw_data_for_item`.
    *   Applies `_filter_by_form_type`.
    *   **Coalesces** the data from synonyms into a single column for each concept (e.g., multiple revenue tags are combined into one "Revenues" column).
    *   Merges the data for all requested concepts into a final DataFrame.
6.  **`_create_plot`**: A helper function to generate Plotly figures, reducing boilerplate in individual metric methods.
7.  **Refactored Metric Methods (Examples)**:
    *   `Revenues`, `NetIncomeLoss`, `CommonStockSharesOutstanding`, `EPS`, `ProfitMargin` are refactored to use `get_financial_data` and `_create_plot`.
    *   They now primarily define the `concept` name(s) they need and let the helper methods do the heavy lifting.
8.  **`compounding_annual_growth_rate`**: Copied and slightly adjusted. It operates on an input DataFrame, so its core logic is less tied to the internal data fetching changes but benefits from `self.company_name`.
9.  **`if __name__ == "__main__":`**: Updated to demonstrate usage of `CompanyV2` and includes basic error handling.

**To complete the refactoring:**

*   Go through each of the original financial metric methods in `company.py`.
*   Identify the core financial concept(s) each method deals with.
*   Ensure these concepts and their synonyms are present in the `GAAP_SYNONYMS` dictionary in `company_v2.py`.
*   Refactor the method to call `self.get_financial_data(gaap_concepts=["YourConcept"], form_type=...)`.
*   If the method performs calculations on multiple fetched items (e.g., `ProfitMargin = NetIncome / Revenues`), fetch all required concepts in one call to `get_financial_data`.
*   Use `self._create_plot` for generating graphs.
*   Thoroughly test each refactored method. The `ShortTermDebt` method, for instance, has specific logic involving summing multiple items and subtracting from another, which will require careful translation to use `get_financial_data` effectively (perhaps by fetching all components and then performing the arithmetic).

This refactoring provides a more maintainable and robust structure. The `get_financial_data` method is now much more powerful and handles the complexity of synonyms and data merging centrally.# filepath: /Users/checomart/Documents/GitHub/44Packages/src/FortyFour/Finance/company_v2.py
 """
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from functools import reduce
from typing import List, Optional, Dict, Any
from FortyFour.Finance.utils import get_all_cik, request_company_filing # Assuming these are correctly imported

class CompanyV2:
    """
    Refactored Company class for fetching and analyzing financial data from SEC filings.
    """

    GAAP_SYNONYMS: Dict[str, List[str]] = {
        "Assets": ["Assets"],
        
        "AssetsCurrent": ["AssetsCurrent"],

        "Capex": [
            'PaymentsToAcquirePropertyPlantAndEquipment', "PaymentsToAcquireOtherPropertyPlantAndEquipment",
            'PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
            "PaymentsToAcquireRealEstateHeldForInvestment", "PaymentsToDevelopRealEstateAssets",
            "PaymentsForCapitalImprovements", 'PaymentsToAcquireAndDevelopRealEstate',
            "PaymentsToAcquireRealEstate", "PaymentsToAcquireCommercialRealEstate",
            "PaymentsToAcquireProductiveAssets",
            "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
            "PurchaseOfPropertyPlantAndEquipmentAndIntangibleAssets", 'PurchasesOfPropertyAndEquipmentAndIntangibleAssets',
        ],

        "CashCashEquivalents": [
            'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
            'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations',
            'CashAndCashEquivalentsAtCarryingValue', 'CashAndCashEquivalents' # Added common variations
        ],

        "CashFromOperatingActivities": [
            'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
            'NetCashProvidedByUsedInOperatingActivities', 'CashFlowsFromUsedInOperatingActivities'
        ],

        "CashFlowFromFinancingActivities": [
            'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
            'NetCashProvidedByUsedInFinancingActivities', 'CashFlowsFromUsedInFinancingActivities'
        ],

        "CashFlowFromInvestingActivities": [
            'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
            'NetCashProvidedByUsedInInvestingActivities', 'CashFlowsFromUsedInInvestingActivities'
        ],

        "CommonStockSharesOutstanding": [
            'WeightedAverageNumberOfDilutedSharesOutstanding', 'CommonStockSharesIssued',
            'EntityCommonStockSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingDiluted',
            'WeightedAverageSharesOutstandingDiluted', 'CommonStockSharesOutstanding'
        ],

        "CostOfGoodsAndServicesSold": ['CostOfGoodsAndServicesSold', 'CostOfRevenue'],
        "DepreciationAndAmortization": [
            'DepreciationAndAmortization', 'DepreciationDepletionAndAmortization',
            'DepreciationAndAmortizationExcludingNuclearFuel'
        ],

        "EarningsPerShareDiluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
        "EffectiveIncomeTaxRateContinuingOperations": ['EffectiveIncomeTaxRateContinuingOperations'],
        "EntityPublicFloat": ["EntityPublicFloat"],
        "Equity": [
            'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            'StockholdersEquity', 'EquityAttributableToOwnersOfParent', 'Equity'
        ],

        "IncomeTaxExpenseBenefit": ['IncomeTaxExpenseBenefit', "IncomeTaxesPaidNet"],
        "InterestExpense": ["InterestExpense", "InterestExpenseNet", "InterestExpenseNetOfHedgeIneffectiveness"],
        "LiabilitiesCurrent": ['LiabilitiesCurrent'],
        "LongTermDebt": [
            'LongTermDebtNoncurrent', 'LongTermDebt', 'LongtermBorrowings',
            "LongTermDebtAndCapitalLeaseObligations", "OtherLiabilitiesNoncurrent",
            'NoncurrentFinancialLiabilities'
        ],

        "MarketableSecuritiesCurrent": ['MarketableSecuritiesCurrent', 'ShortTermInvestments'],
        "NetIncomeLoss": [
            "NetIncomeLoss", 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic',
            'ProfitLossAttributableToOwnersOfParent'
        ],

        "OperatingIncomeLoss": [
            "OperatingIncomeLoss",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromOperationsBeforeIncomeTaxExpenseBenefit"
        ],

        "PropertyPlantAndEquipmentGross": [
            "PropertyPlantAndEquipmentGross", "RealEstateInvestmentPropertyAtCost",
            "GrossInvestmentInRealEstateAssets", 'PropertyPlantAndEquipment' # Note: 'PropertyPlantAndEquipment' can be ambiguous (net or gross)
        ],

        "PropertyPlantAndEquipmentNet": [
            "PropertyPlantAndEquipmentNet", "NetInvestmentInRealEstateAssets",
            'RealEstateInvestmentPropertyNet', 'PropertyPlantAndEquipment'
        ],

        "Revenues": [
            'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet',
            'Revenue', 'RevenueFromSaleOfGoods', 'RevenueFromContractsWithCustomers', 'NoninterestIncome'
        ],

        "ShortTermPayablesForDebtCalc": [ # Specific group for ShortTermDebt calculation
            "TradeAndOtherCurrentPayables", "AccountsPayableCurrent", "EmployeeRelatedLiabilitiesCurrent",
            "CurrentTaxLiabilitiesCurrent", "AccruedIncomeTaxesCurrent", "OtherShorttermProvisions",
            "LiabilitiesIncludedInDisposalGroupsClassifiedAsHeldForSale",
            "ContractWithCustomerLiabilityCurrent", "AccountsPayableAndAccruedLiabilitiesCurrent",
            "AccruedLiabilitiesCurrent", "AccruedRebatesReturnsAndPromotions", "OtherLiabilitiesCurrent"
        ],
        # Add other concepts and their synonyms here
    }


    def __init__(self, ticker: str, cik: Optional[str] = None, logo_path: Optional[str] = None):
        """
        Initialize the CompanyV2 instance with a ticker and optional CIK.
        If CIK is not provided, it will be looked up using the ticker.
        """
        self.ticker = ticker
        self.cik = cik
        self.logo_path = logo_path
        self.company_name = None
        self.GAAP_NORM = None
        self._facts = None

        if not self.cik:
            try:
                cik_df = get_all_cik()
                if not cik_df.empty and 'cik' in cik_df.columns and 'ticker' in cik_df.columns:
                    cik_row = cik_df[cik_df['ticker'] == self.ticker]
                    if not cik_row.empty:
                        self.cik = cik_row.iloc[0]['cik']
                    else:
                        raise ValueError(f"CIK for ticker {self.ticker} not found.")
                else:
                    raise ValueError("CIK DataFrame is empty or missing required columns.")
            except Exception as e:
                logging.error(f"Error fetching CIK for ticker {self.ticker}: {e}")
                raise

        # Fetch company name and GAAP norm
        try:
            filing_data = request_company_filing(self.cik)
            if filing_data and 'companyName' in filing_data and 'facts' in filing_data:
                self.company_name = filing_data['companyName']
                self._facts = filing_data['facts']
                self.GAAP_NORM = next((norm for norm in ['us-gaap', 'ifrs-full'] if norm in self._facts), None)
            else:
                raise ValueError(f"Invalid data structure returned for CIK {self.cik}.")
        except Exception as e:
            logging.error(f"Error fetching company data for CIK {self.cik}: {e}")
            raise

if __name__ == "__main__":
    pass