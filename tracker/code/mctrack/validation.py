"""Functions for validation of day2 schema"""
import json
import logging

import iso8601
import jsonschema


def schema_validate(record_str, day2_schema):

    retval = None
    # 1. Try to decode it into utf-8
    # 2. Try to check if it is a valid json
    try:
        retval = json.loads(record_str)
        if day2_schema is not None:
            jsonschema.validate(retval, day2_schema)
    except UnicodeError as unicode_error:
        logging.debug("ERROR: Invalid record: %s : rec=%s",
                      str(unicode_error), record_str)
        retval = None
    except jsonschema.ValidationError as val_error:
        logging.debug("ERROR: Invalid record: %s : rec=%s",
                      str(val_error), record_str)
        retval = None
    except jsonschema.SchemaError as schema_error:
        logging.debug("ERROR: Invalid schema: %s : rec=%s",
                      str(schema_error), day2_schema)
        retval = None
    except ValueError as value_error:
        logging.debug("ERROR: Invalid record: %s : rec=%s",
                      str(value_error), record_str)
        retval = None
    return retval


def check_timestamp(json_ele):
    """"
    Function to check timestamp is valid

    Arguments:
        json_ele {dict} -- The detection dictionary as a day2 schema

    Returns:
        bool -- True if json_ele["@timestamp"] is valid. False otherwise
    """

    try:
        if json_ele is None or json_ele.get("@timestamp", None) is None:
            return False
        _ = iso8601.parse_date(json_ele['@timestamp'])
    except iso8601.ParseError:
        return False
    return True


def ignore_bad_records(json_list):
    """
    Function that ignores badly formatted json_list. This function should be
    called before other processing functions so that we do not crash on bad
    record formats

    Arguments:
        json_list {list} -- list of detections in day2 format

    Returns:
        list -- list of valid records
    """

    retval = []
    check_fn_list = [check_timestamp]
    for json_ele in json_list:
        if json_ele is not None:
            valid = True
            for myfn in check_fn_list:
                if not myfn(json_ele):
                    valid = False
                    break
            if valid:
                retval.append(json_ele)
    return retval
