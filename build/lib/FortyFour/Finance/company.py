import pandas as pd
import logging
from enum import Enum
from FortyFour.Finance.utils import request_company_filing, SECCache


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


class Company:
    """
    A class representing a company with its CIK and name.
    """
    def __init__(self, cik: str, name: str, cache: SECCache = None):
        # Ensure CIK is correctly formatted (10 digits, optionally prefixed with CIK)
        self.cik = str(cik).zfill(10)
        if not self.cik.startswith("CIK"):
            self.cik = f"CIK{self.cik}"
        self.name = name
        self.cache = cache
        self._filing_data = None

    @property
    def filing_data(self):
        """
        Lazy-load filing data from cache or API.
        """
        if self._filing_data is None:
            self._filing_data = request_company_filing(self.cik, cache=self.cache)
            if not self._filing_data:
                logging.error(f"Failed to fetch filing data for CIK {self.cik}")
        return self._filing_data

    def get_raw_fact(self, tag_name: str, filings_type: str = "10-K") -> pd.Series:
        """
        Retrieve a specific XBRL tag from the filing data as a time-series.
        """
        data = self.filing_data
        if not data or "facts" not in data:
            return pd.Series(dtype=float)
            
        collected = []
        # Search across all fact types (us-gaap, dei, etc.)
        facts = data.get("facts", {})
        for fact_type_data in facts.values():
            if not isinstance(fact_type_data, dict):
                continue
            if tag_name in fact_type_data:
                units = fact_type_data[tag_name].get("units", {})
                for entries in units.values():
                    for entry in entries:
                        if entry.get("form") == filings_type:
                            collected.append(entry)
        
        if not collected:
            return pd.Series(dtype=float)
            
        df = pd.DataFrame(collected)
        df["end"] = pd.to_datetime(df["end"], format="%Y-%m-%d", errors='coerce')
        # Sort by end date, then by filed date (latest first) to handle restatements
        df = df.sort_values(by=["end", "filed"], ascending=[True, False])
        # Drop duplicates for the same end date, keeping the latest filed one
        df = df.drop_duplicates(subset=["end"], keep="first")
        
        # Return as a Series with Date index
        series = df.set_index("end")["val"]
        series.index.name = "Date"
        return series

    def get_financial(self, gaap_concept: GAAP, filings_type: str ="10-Q") -> pd.DataFrame:
        """
        Extract financial data for a given GAAP concept and filing type.
        (Backward compatible method)
        """
        synonyms = gaap_concept.value[1]
        
        # Try synonyms one by one
        found_series = None
        found_tag = None
        
        for tag in synonyms:
            series = self.get_raw_fact(tag, filings_type=filings_type)
            if not series.empty:
                found_series = series
                found_tag = tag
                break
                
        if found_series is None:
            logging.info(f"No data found for {gaap_concept.name} for CIK {self.cik}")
            return pd.DataFrame()
            
        # Reconstruct DataFrame for backward compatibility
        df = found_series.reset_index()
        df.columns = ["Date", gaap_concept.value[0]]
        return df


if __name__ == "__main__":
    # Example CIK for Apple Inc.
    apple_cik = "0000320193"

    company = Company(cik=apple_cik, name="Apple Inc.")
    
    # Fetch some sample data
    rev_df = company.get_financial(gaap_concept=GAAP.REVENUES, filings_type="10-K")
    shares_df = company.get_financial(gaap_concept=GAAP.COMMON_STOCK_SHARES_OUTSTANDING, filings_type="10-K")
    
    print(f"Revenues for {company.name}:")
    print(rev_df.tail())
    print("\n" + "*" * 20 + "\n")
    print(f"Shares Outstanding for {company.name}:")
    print(shares_df.tail())
