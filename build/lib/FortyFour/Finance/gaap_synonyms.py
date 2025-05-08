from typing import List, Optional, Dict, Any
from enum import Enum
from typing import List, Tuple, Optional


# This file contains a dictionary of GAAP concepts and their synonyms.
# The keys are the canonical names of the concepts, and the values are lists of synonyms.
# The purpose of this dictionary is to provide a mapping between different names for the same concept,
# which can be useful for data analysis and reporting.

# Note: You will need to adjust the file-level imports.
# Ensure 'Enum' is imported from 'enum', and 'List', 'Tuple', 'Optional' from 'typing'.
# The original 'Dict' and 'Any' from typing might no longer be needed if this Enum replaces all uses of the old dictionary.

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
        'EntityCommonStockSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingDiluted',
        'WeightedAverageSharesOutstandingDiluted', 'CommonStockSharesOutstanding'
    ])
    COST_OF_GOODS_AND_SERVICES_SOLD = ("CostOfGoodsAndServicesSold", ['CostOfGoodsAndServicesSold', 'CostOfRevenue'])
    
    DEPRECIATION_AND_AMORTIZATION = ("DepreciationAndAmortization", [
        'DepreciationAndAmortization', 'DepreciationDepletionAndAmortization',
        'DepreciationAndAmortizationExcludingNuclearFuel'
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
    # Add other concepts and their synonyms here following the same pattern

if __name__ == "__main__":
    # Example of accessing an enum member
    selected_member = GAAP.ASSETS

    # Accessing the canonical name
    canonical_name = selected_member.value[0]

    # Accessing the list of synonyms
    synonyms = selected_member.value[1]

    print(f"Selected Member: {selected_member.name}")
    print(f"Canonical Name: {canonical_name}")
    print(f"Synonyms: {synonyms}")

    # Example with another member
    selected_member_capex = GAAP.CAPEX
    canonical_name_capex = selected_member_capex.value[0]
    synonyms_capex = selected_member_capex.value[1]

    print(f"\nSelected Member: {selected_member_capex.name}")
    print(f"Canonical Name: {canonical_name_capex}")
    print(f"Synonyms: {synonyms_capex}")


