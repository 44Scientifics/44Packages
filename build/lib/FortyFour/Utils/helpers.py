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
    new_list: List[Dict[str, Any]],
    key: str,
    defaults: Optional[Dict[str, Any]] = None,
    merge_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Merge two lists of dictionaries based on a unique key field.

    Parameters:
        old_list: Existing list of dicts (may be None or empty).
        new_list: Updated list of dicts. Each dict must contain the key.
        key: The field name used to match records between lists.
        defaults: Default values for any new records (merged into record).
        merge_fn: Optional function(old_record, new_record) -> merged_record.
            Called when a record exists in both lists to combine them.
            If not provided, the old record is preserved as-is.

    Returns:
        A list of merged dicts, ordered as in new_list.
    """
    defaults = defaults or {}
    # Index old list by the key (make copies to avoid mutating originals)
    old_index: Dict[Any, Dict[str, Any]] = {
        item[key]: item.copy() for item in (old_list or []) if key in item
    }

    merged: List[Dict[str, Any]] = []
    for new_rec in new_list:
        rec_id = new_rec.get(key)
        if rec_id in old_index:
            old_rec = old_index[rec_id]
            if merge_fn:
                merged_rec = merge_fn(old_rec, new_rec)
            else:
                merged_rec = old_rec
        else:
            # Create a new record with defaults, then update with new_rec
            merged_rec = {**defaults}
            merged_rec.update(new_rec)
        merged.append(merged_rec)

    return merged

