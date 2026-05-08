import pandas as pd
import logging

class MetricRegistry:
    """
    A registry for financial metrics and their calculation formulas.
    """
    def __init__(self):
        self.metrics = {}

    def register(self, name, components, formula):
        """
        Register a new metric.
        
        Args:
            name (str): The name of the metric.
            components (dict): Mapping of argument names to lists of SEC synonyms.
            formula (callable): A function that takes components as arguments and returns a result.
        """
        self.metrics[name] = {"components": components, "formula": formula}

class MetricEngine:
    """
    An engine for calculating metrics registered in a MetricRegistry.
    """
    def __init__(self, registry: MetricRegistry):
        self.registry = registry

    def calculate(self, company, metric_name, filings_type="10-K") -> pd.Series:
        """
        Calculate a metric for a given company.
        """
        if metric_name not in self.registry.metrics:
            raise ValueError(f"Metric {metric_name} not found in registry.")
            
        recipe = self.registry.metrics[metric_name]
        data_components = {}
        
        # Fetch each component using synonyms
        for arg_name, synonyms in recipe["components"].items():
            found_data = pd.Series(dtype=float)
            for tag in synonyms:
                found_data = company.get_raw_fact(tag, filings_type=filings_type)
                if not found_data.empty:
                    break
            
            if found_data.empty:
                logging.warning(f"Required component '{arg_name}' not found for {company.name}")
                return pd.Series(dtype=float)
            
            data_components[arg_name] = found_data

        # Align all components by Date (outer join)
        # We use a DataFrame to align everything and handle missing values
        df = pd.concat(data_components.values(), axis=1, keys=data_components.keys())
        
        # Sort by date and forward-fill to align disparate reporting dates if necessary
        df = df.sort_index().ffill()
        
        # Apply the formula
        try:
            # We pass each column as an argument to the formula function
            result = recipe["formula"](**{k: df[k] for k in data_components.keys()})
            return result
        except Exception as e:
            logging.error(f"Error calculating {metric_name} for {company.name}: {e}")
            return pd.Series(dtype=float)
