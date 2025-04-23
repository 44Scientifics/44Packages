import numpy as np
from dateutil.parser import parse
from datetime import datetime
import logging
from typing import List, Dict, Callable, Any, Optional


def serialize_date_in_dict(my_dict: dict):
    for key, value in my_dict.items():
        if isinstance(value, dict):
            value = serialize_date_in_dict(value)
        try:
            my_dict[key] = parse(value)
            my_dict[key] = datetime.combine(my_dict[key], datetime.min.time())
        except:
            # print("convert_string_to_date_in_dict() as encounter an exception")
            pass
    return my_dict


def remove_nan_values_from_dict(my_dict: dict):
    """
    > This is a recursive function that can remove None values from simple and nested dictionary.
    The function will check each value in the dictionary. if the value is another dict, the function will call
    itself with the nested dictionary as the argument.

    > This function will dig down into the structure of the input dictionary, regardless of how many levels of nesting there are,
    and remove all None values.

    Args:
        my_dict:        This is the dict you want to clean out of None values

    Returns: dict

    """
    clean_dict = {}
    for key, value in my_dict.items():
        if isinstance(value, dict):
            value = remove_nan_values_from_dict(value)
        if value is not np.nan:
            clean_dict[key] = value
    return clean_dict


def convert_string_to_date_in_dict(my_dict: dict):
    for key, value in my_dict.items():
        if isinstance(value, dict):
            value = convert_string_to_date_in_dict(value)
        try:
            my_dict[key] = parse(value)
            my_dict[key] = datetime.combine(my_dict[key], datetime.min.time())
        except Exception as e:
            logging.warning('The function convert_string_to_date_in_dict(my_dict) encounter an exeption: ', e)
            pass
    return my_dict


def sort_dict_by_key(my_dict: dict, key: str, reverse: bool):
    newlistOfDict = sorted(my_dict, key=lambda d: d[key], reverse=reverse)
    return newlistOfDict



def update_list_from_new_source_keep_old_matches(
    old_list: Optional[List[Dict[str, Any]]],
    new_list: Optional[List[Dict[str, Any]]],
    default_fields: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Merge old and new symbol entries, preserving existing data and removing deprecated symbols.

    Behavior:
      1. Removes any symbol present in old_list but absent from new_list.
      2. For each symbol in new_list:
         - If it exists in old_list, preserve all old properties and override them with new_list values.
         - If it is new, initialize missing fields from default_fields.
      3. Ensures every merged symbol has required keys.

    Args:
        old_list: Existing list of symbol documents (each with '_id', 'ticker', etc.).
        new_list: Updated list of symbol documents.
        default_fields: Defaults for new or missing fields (e.g. 'avg_price', 'nb_shares', 'cost_basis', 'comment' or 'score').

    Returns:
        A list of merged symbol dicts ready for storage.

    Raises:
        KeyError: If a merged entry is missing '_id' or 'ticker'.
    """
    # Initialize defaults
    if default_fields is None:
        default_fields = {
            'avg_price': 0.0,
            'nb_shares': 0.0,
            'cost_basis': 0.0,
        }

    # Build a lookup for old entries
    old_map: Dict[Any, Dict[str, Any]] = {item['_id']: item for item in (old_list or [])}

    merged: List[Dict[str, Any]] = []

    # Iterate only over new_list to add or update
    for new_item in (new_list or []):
        key = new_item.get('_id')
        if key is None:
            raise KeyError(f"New entry missing '_id': {new_item}")

        # Start with defaults, then old data, then new overrides
        base = old_map.get(key, {})
        combined = {**default_fields, **base, **new_item}

        # Validate required fields
        if '_id' not in combined or 'ticker' not in combined:
            raise KeyError(f"Merged symbol entry missing required keys: {combined}")

        merged.append(combined)

    return merged
