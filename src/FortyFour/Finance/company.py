import json
import requests
import pandas as pd
import logging
from enum import Enum



class GAAP(Enum):
    """
    Enumeration of GAAP concepts, each holding its canonical name and a list of synonyms.
    """
    ASSETS = ("Assets", ["Assets"])

    ASSETS_CURRENT = ("AssetsCurrent", ["AssetsCurrent"])
    CAPEX = ("Capex", [
        'PaymentsToAcquirePropertyPlantAndEquipment', "PaymentsToAcquireOtherPropertyPlantAndEquipment",
        'PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
        "PaymentsToAcquireRealEstateHeldForInvestment", "PaymentsToDevelopRealEstateAssets",
        "PaymentsForCapitalImprovements", 'PaymentsToAcquireAndDevelopRealEstate',
        "PaymentsToAcquireRealEstate", "PaymentsToAcquireCommercialRealEstate",
        "PaymentsToAcquireProductiveAssets",
        "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
        "PurchaseOfPropertyPlantAndEquipmentAndIntangibleAssets", 'PurchasesOfPropertyAndEquipmentAndIntangibleAssets',
    ])
    CASH_CASH_EQUIVALENTS = ("CashAndCashEquivalentsAtCarryingValue", [
        'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
        #'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations',
        'CashAndCashEquivalentsAtCarryingValue', 'CashAndCashEquivalents'
    ])
    CASH_FROM_OPERATING_ACTIVITIES = ("CashFromOperatingActivities", [
        'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
        'NetCashProvidedByUsedInOperatingActivities', 'CashFlowsFromUsedInOperatingActivities'
    ])
    CASH_FLOW_FROM_FINANCING_ACTIVITIES = ("CashFlowFromFinancingActivities", [
        'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
        'NetCashProvidedByUsedInFinancingActivities', 'CashFlowsFromUsedInFinancingActivities'
    ])
    CASH_FLOW_FROM_INVESTING_ACTIVITIES = ("CashFlowFromInvestingActivities", [
        'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
        'NetCashProvidedByUsedInInvestingActivities', 'CashFlowsFromUsedInInvestingActivities'
    ])
    COMMON_STOCK_SHARES_OUTSTANDING = ("CommonStockSharesOutstanding", [
        'WeightedAverageNumberOfDilutedSharesOutstanding', 'CommonStockSharesIssued',
        'EntityCommonStockSharesOutstanding', 
        'WeightedAverageNumberOfSharesOutstandingDiluted',
        'WeightedAverageSharesOutstandingDiluted', 'CommonStockSharesOutstanding'
    ])
    PAYMENT_FOR_SHARE_BUYBACKS = ("ShareBuybacks", [
        'PaymentsForRepurchaseOfCommonStock', 'PaymentsForRepurchaseOfCommonStockIncludingDisposalGroupAndDiscontinuedOperations',
        'PaymentsForRepurchaseOfCommonStockIncludingDisposalGroup', 'PaymentsForRepurchaseOfCommonStockExcludingDisposalGroup',
        'PaymentsForRepurchaseOfCommonStockExcludingDiscontinuedOperations'
    ])
    
    COST_OF_GOODS_AND_SERVICES_SOLD = ("CostOfGoodsAndServicesSold", ['CostOfGoodsAndServicesSold', 'CostOfRevenue'])
    
    DEPRECIATION_AND_AMORTIZATION = ("DepreciationAndAmortization", [
        'DepreciationAndAmortization', 'DepreciationDepletionAndAmortization',
        'DepreciationAndAmortizationExcludingNuclearFuel'
    ])
    DIVIDEND_PER_SHARE = ("DividendPerShare", [
        "CommonStockDividendsPerShareCashPaid", "CommonStockDividendsPerShareDeclared",
        "DividendsRecognisedAsDistributionsToOwnersPerShare"
    ])
    
    EARNINGS_PER_SHARE_DILUTED = ("EarningsPerShareDiluted", ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"])
    
    EFFECTIVE_INCOME_TAX_RATE_CONTINUING_OPERATIONS = ("EffectiveIncomeTaxRateContinuingOperations", ['EffectiveIncomeTaxRateContinuingOperations'])
    
    ENTITY_PUBLIC_FLOAT = ("EntityPublicFloat", ["EntityPublicFloat"])
    
    EQUITY = ("Equity", [
        'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
        'StockholdersEquity', 'EquityAttributableToOwnersOfParent', 'Equity'
    ])
    
    INCOME_TAX_EXPENSE_BENEFIT = ("IncomeTaxExpenseBenefit", ['IncomeTaxExpenseBenefit', "IncomeTaxesPaidNet"])
    
    INTEREST_EXPENSE = ("InterestExpense", ["InterestExpense", "InterestExpenseNet", "InterestExpenseNetOfHedgeIneffectiveness"])
    
    LIABILITIES_CURRENT = ("LiabilitiesCurrent", ['LiabilitiesCurrent'])
    
    LONG_TERM_DEBT = ("LongTermDebt", [
        'LongTermDebtNoncurrent', 'LongTermDebt', 'LongtermBorrowings',
        "LongTermDebtAndCapitalLeaseObligations", "OtherLiabilitiesNoncurrent",
        'NoncurrentFinancialLiabilities'
    ])
    MARKETABLE_SECURITIES_CURRENT = ("MarketableSecuritiesCurrent", ['MarketableSecuritiesCurrent', 'ShortTermInvestments'])
    NET_INCOME_LOSS = ("NetIncomeLoss", [
        "NetIncomeLoss", 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic',
        'ProfitLossAttributableToOwnersOfParent'
    ])
    OPERATING_INCOME_LOSS = ("OperatingIncomeLoss", [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromOperationsBeforeIncomeTaxExpenseBenefit"
    ])
    PAYMENT_OF_DIVIDENDS = ("PaymentsOfDividends", ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends", 'PaymentsOfOrdinaryDividends',
                    'DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities',
                    'DividendsPaidClassifiedAsFinancingActivities'])
    
    PROPERTY_PLANT_AND_EQUIPMENT_GROSS = ("PropertyPlantAndEquipmentGross", [
        "PropertyPlantAndEquipmentGross", "RealEstateInvestmentPropertyAtCost",
        "GrossInvestmentInRealEstateAssets", 'PropertyPlantAndEquipment'
    ])
    PROPERTY_PLANT_AND_EQUIPMENT_NET = ("PropertyPlantAndEquipmentNet", [
        "PropertyPlantAndEquipmentNet", "NetInvestmentInRealEstateAssets",
        'RealEstateInvestmentPropertyNet', 'PropertyPlantAndEquipment'
    ])
    REVENUES = ("Revenues", [
        'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet',
        'Revenue', 'RevenueFromSaleOfGoods', 'RevenueFromContractsWithCustomers', 'NoninterestIncome'
    ])
    SHORT_TERM_PAYABLES_FOR_DEBT_CALC = ("ShortTermPayablesForDebtCalc", [
        "TradeAndOtherCurrentPayables", "AccountsPayableCurrent", "EmployeeRelatedLiabilitiesCurrent",
        "CurrentTaxLiabilitiesCurrent", "AccruedIncomeTaxesCurrent", "OtherShorttermProvisions",
        "LiabilitiesIncludedInDisposalGroupsClassifiedAsHeldForSale",
        "ContractWithCustomerLiabilityCurrent", "AccountsPayableAndAccruedLiabilitiesCurrent",
        "AccruedLiabilitiesCurrent", "AccruedRebatesReturnsAndPromotions", "OtherLiabilitiesCurrent"
    ])



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
         # Ensure CIK is 10 digits
        self.cik = "CIK"+str(cik).zfill(10) if not str(cik).startswith("CIK") else str(cik)
        self.name = name

        # request the company filing data
        try:
            self.filing_data = request_company_filing(self.cik)
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch initial data for CIK {self.cik} during initialization: {e}")
            self.filing_data = None # Or handle more gracefully, e.g., raise exception




    def get_financial(self, gaap_concept: GAAP, filings_type: str ="10-Q") -> pd.DataFrame:
        
        # Use the data fetched during initialization
        if self.filing_data is None:
            print(f"Filing data for CIK {self.cik} is not available. Please check the initialization.")
            logging.error(f"No filing data available for CIK {self.cik}, possibly due to an earlier fetch failure.")
            return pd.DataFrame()
        
        data = self.filing_data # Use pre-fetched data

        
        canonical_name = gaap_concept.value[0]
        synonyms = gaap_concept.value[1]
        
        collected_entries = []
        
                    
        # Iterate over all fact types (e.g., 'us-gaap', 'dei', 'invest', 'srt')
        if data.get("facts"):
            for fact_type in data["facts"].keys():
        
                # Then check synonyms
                for key in synonyms:
                    if data["facts"][fact_type] and key in data["facts"][fact_type]:
                        if "units" in data["facts"][fact_type][key]:
                            for unit_name in data["facts"][fact_type][key]["units"]:
                                for entry in data["facts"][fact_type][key]["units"][unit_name]:
                                    entry_copy = entry.copy()
                                    entry_copy['source_key'] = key
                                    entry_copy['unit'] = unit_name
                                    #entry_copy['is_canonical'] = False
                                    entry_copy['fact_type'] = fact_type
                                    collected_entries.append(entry_copy)

        if not collected_entries:
            logging.info(f"No data found for {gaap_concept.name} for CIK {self.cik} using specified keys.")
            return pd.DataFrame()

        # Filter by the specified filings type
        filtered_by_form = [entry for entry in collected_entries if entry.get("form") == filings_type]

        if not filtered_by_form:
            logging.info(f"No data found for {gaap_concept.name} for CIK {self.cik} with form type {filings_type}.")
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
            logging.info(f"No unique data entries found after processing for {gaap_concept.name} for CIK {self.cik} with form type {filings_type}.")
            return pd.DataFrame()

        df = pd.DataFrame(deduplicated_entries)
        # Select and order columns for the final DataFrame
        #df = df[["end", "val", "accn", "form","", "source_key", "is_canonical"]]
        df["end"] = pd.to_datetime(df["end"], format="%Y-%m-%d", errors='coerce')
        # Final sort by end date for presentation
        df = df.sort_values(by=["end", "val"]).reset_index(drop=True)
        # Rename columns for clarity
        df.rename(columns={'val': gaap_concept.value[0], 'end': 'Date'}, errors="ignore", inplace=True)
        df.drop(columns=["start", "fy","fp","frame"], inplace=True, errors="ignore")
        
        # Set index to Date
        #df.set_index("Date", inplace=True)
        # remove duplicates based on the accn, keep the last one
        df.drop_duplicates(subset=["accn"],keep="last", inplace=True)
        
        
        # drop duplicates based on the date
        
        
       
        return df


if __name__ == "__main__":
    # Create a Company instance
    apple_cik = 789019

    company = Company(cik=apple_cik, name="Apple Inc.")
    # Example CIK for Apple Inc.
    capex_df = company.get_financial(gaap_concept=GAAP.DIVIDEND_PER_SHARE, filings_type="10-K")
    cash_df = company.get_financial(gaap_concept=GAAP.COMMON_STOCK_SHARES_OUTSTANDING, filings_type="10-K")
    #print(capex_df)
    print("*" * 20)
    print(cash_df)
