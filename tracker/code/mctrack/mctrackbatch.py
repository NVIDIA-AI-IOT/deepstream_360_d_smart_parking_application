"""
This module is to use Multi-cam tracking in streaming mode
"""


__version__ = '0.2'

import json
from timeit import default_timer as timer
import logging

from . import ioutils, trackerutils, mctracker, constants


def read_schema_and_infer(schema_json_file, config_file="config.json"):
    """
    Function to read an entire json schema file and mctrack from it

    Returns:
        [list] -- List of Day2 schema dictionaries with tracked object ids
    """

    config = json.load(open(config_file))
    ignore_dict = config.get(
        "IGNORE_DETECTION_DICT_MOVING", {})
    # One time creation of polygons
    ignore_poly_dict = ioutils.create_poly_dict(ignore_dict)

    start_end_times = config.get("timeRange", {})
    resample_time_secs = config.get(
        "resample_time_sec", constants.RESAMPLE_TIME_IN_SEC)
    json_list = ioutils.read_json_list(schema_json_file, start_end_times)
    points_list, ignored_list = ioutils.ignore_false_detections(
        json_list, ignore_poly_dict)

    mctracker_obj = mctracker.MulticamTracker(config)
    _ = mctracker_obj.mclogger.log_input_points(points_list, ignored_list, 0)

    retval = []
    index = 0
    time_indexed_json_dict = trackerutils.create_time_windows(
        points_list, resample_time_secs)
    for timestamp in time_indexed_json_dict.keys():

        all_json_list = time_indexed_json_dict[timestamp]

        if all_json_list:
            start_time = timer()

            mctracker_obj.process_batch(all_json_list)
            end_time = timer()

            state_sizes = {
                "unidentified_cars": len(mctracker_obj.state.unidentified_cars),
                "prev_list": len(mctracker_obj.state.prev_list),
                "carry_over_list": len(mctracker_obj.state.carry_over_list),
                "retval": len(mctracker_obj.state.retval),
                "match_stats": len(mctracker_obj.state.match_stats),
                "possible_parked_cars": len(mctracker_obj.state.possible_parked_cars),
            }
            logging.info("Re-Id Batch: Time taken: %f: State sizes: %s",
                         float(end_time - start_time), str(state_sizes))
            tmp_ret = mctracker_obj.state.retval
            if tmp_ret is not None:
                mctracker_obj.remove_all_additional_fields(tmp_ret)
                retval += tmp_ret

            index += 1

    mctracker_obj.remove_all_additional_fields(retval)
    # retval = fix_movement_after_park(retval)
    # retval = super_smooth_end_trajs(retval, prune_dist_thresh=20)
    mctracker_obj.mclogger.close_debug_files()
    return retval
