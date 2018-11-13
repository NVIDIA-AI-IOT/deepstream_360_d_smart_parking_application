"""Module to handle all file reads and discarding ignored regions
"""

__version__ = '0.2'

import json

import iso8601
from shapely.geometry import Point, Polygon

from . import trackerutils


def remove_inferred(gt_json_list):
    """Remove all unnecessary records
    Unnecessary records = ["reset]

    Arguments:
        gt_json_list {[list]} -- List of Day2 detection dictionaries

    Returns:
        [list] -- List of Day2 detection dictionaries with relevant records
    """
    json_list = []
    id_so_far = 0
    for json_ele in gt_json_list:
        event = json_ele.get('event', None)
        if event is not None:
            if event.get('type', None) not in ['reset']:
                json_list.append(json_ele)
        id_so_far += 1
    return json_list


def is_within_time_range(json_ele, start_time, end_time):
    """Checks if the day2 dict is within the given timerange
    [start_time, end_time)
    NOTE: start_time is inclusive, and end_time is exclusive
    If start_time is None, then start is not checked
    If end_time is None, then end is not checked

    Arguments:
        json_ele {dict} -- Vehicle detection in day2 schema
        start_time {datetime} -- start_time
        end_time {datetime} -- end_time
    """
    is_in_range = False
    json_time = iso8601.parse_date(json_ele["@timestamp"])
    if start_time is None or json_time >= start_time:
        # We are after start
        if end_time is None or json_time < end_time:
            # We are before end
            is_in_range = True
    return is_in_range


def read_json_list(schema_json_file, start_end_times):
    """
    Read jsons from a file. The file is assumed to contain jsons in
    day2 schema. Each line will have one record, and no empty or invalid
    lines

    Arguments:
        schema_json_file {[string]} -- File from which to read jsons

    Returns:
        [list] -- List of Day2 detection dictionaries
    """
    gt_json_list = []
    start_time = start_end_times.get("start", None)
    end_time = start_end_times.get("end", None)
    if start_time is not None:
        start_time = iso8601.parse_date(start_time)
    if end_time is not None:
        end_time = iso8601.parse_date(end_time)
    with open(schema_json_file, 'r') as fileptr:
        for line in fileptr:
            line = line.strip()
            json_ele = json.loads(line)
            if is_within_time_range(json_ele, start_time, end_time):
                gt_json_list.append(json_ele)
    json_list = remove_inferred(gt_json_list)
    return json_list


def create_poly_dict(sensor_polypts_dict):
    """
    Create a polygon dictionary from a list of polygon points
    This can be used for one time creation of polygons so that we
    dont have to repeadly construct polygons while checking points
    (especially in a streaming mode)

    Arguments:
        sensor_polypts_dict {dict} -- dictionary containing
            key = some id (e.g., sensor id)
            value = list of points (x,y) that make the polygon

    Returns:
        dict -- dictionary containing
            key = some id (e.g., sensor id)
            value = shapely's polygon object
    """
    poly_dict = {sensor:
                 [Polygon(poly) for poly in sensor_polypts_dict[sensor]]
                 for sensor in sensor_polypts_dict
                 }
    return poly_dict


def ignore_false_detections(json_list, ignore_dict):
    """
    There might be some areas where vehicle detections are to be ignored
    (e.g., because of a lot of FPs in those areas). This function
    removes such detections that fall into "ignored" areas

    Arguments:
        json_list {[list]} -- List of Day2 detection dictionaries
        ignore_dict {[list]} -- dictionary of regions to
            be ignored. It will be in the format:
                key = camera name
                value = list of polygons (shapely.Polygon objects) to be
                    ignored

    Returns:
        [list] -- List of Day2 detection dictionaries
    """
    retval = []
    ignored_list = []
    for ele in json_list:
        ignore = False
        if trackerutils.is_aisle_rec(ele):
            sensor_id = ele.get("sensor", {}).get("id", None)
            if sensor_id is not None:
                ignore_list = ignore_dict.get(sensor_id, None)
                if ignore_list is not None:
                    # Check if the point falls within the polygon
                    point = trackerutils.get_xy(ele)
                    if point is not None:
                        point = Point(point)
                        for polygon in ignore_list:
                            if polygon.contains(point):
                                ignore = True
                                break
        if not ignore:
            retval.append(ele)
        else:
            ignored_list.append(ele)
    return retval, ignored_list
