import numpy as np
from dateutil.parser import parse
from datetime import datetime
import json
import logging


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
    datetime.now().isoformat()


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
