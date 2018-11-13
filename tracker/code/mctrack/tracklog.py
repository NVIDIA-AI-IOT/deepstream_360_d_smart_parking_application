"""
Module for logging tracking info
"""

__version__ = '0.2'

from . import constants
from . import trackerutils

# Files for logging

DEBUG_CLUSTER_FILE = "./cluster.log"
DEBUG_MATCH_FILE = "./matching.log"
DEBUG_INP_POINTS_FILE = "./inputPoints.log"
"""
DEBUG_CLUSTER_FILE = None
DEBUG_MATCH_FILE = None
DEBUG_INP_POINTS_FILE = None
"""


class MulticamTrackLogger:
    """
    This class is responsible for logging all tracker events. The logs are
    currently used for visualizing output at each timestep, or for measuring
    timings of multicam tracking module.
    """

    def __init__(self, config):
        """
        Initialization

        Returns: None
        """
        self.debug_cluster_fp = None
        self.debug_match_fp = None
        self.debug_input_points_fp = None
        self.resample_time_secs = config.get(
            "resample_time_sec", constants.RESAMPLE_TIME_IN_SEC)

        if DEBUG_CLUSTER_FILE is not None:
            self.debug_cluster_fp = open(DEBUG_CLUSTER_FILE, 'w')
            self.debug_cluster_fp.write(
                "key,timestamp,cid,x,y,cam,vehicle,objid,placeId\n")

        if DEBUG_INP_POINTS_FILE is not None:
            self.debug_input_points_fp = open(DEBUG_INP_POINTS_FILE, 'w')
            self.debug_input_points_fp.write(
                "key,id,tsbin,timestamp,event,x,y,cam,vehicle,objid,placeId,ignored\n")

        if DEBUG_MATCH_FILE is not None:
            self.debug_match_fp = open(DEBUG_MATCH_FILE, 'w')
            self.debug_match_fp.write(
                "key,timestamp1,timestamp2,match_id,x1,y1,cam1,veh1,"
                "objid1,placeid1,x2,y2,cam2,veh2,objid2,placeid2\n")

    def close_debug_files(self):
        """
        This method closes all the open debug files. This function has to be
        explicity called after multi-cam tracking module is finished
        """

        if self.debug_cluster_fp is not None:
            self.debug_cluster_fp.close()
            self.debug_cluster_fp = None

        if self.debug_match_fp is not None:
            self.debug_match_fp.close()
            self.debug_match_fp = None

        if self.debug_input_points_fp is not None:
            self.debug_input_points_fp.close()
            self.debug_input_points_fp = None

    def flush_files(self):
        """Flush the log files, if logging is enabled
        """
        if self.debug_cluster_fp is not None:
            self.debug_cluster_fp.flush()

        if self.debug_match_fp is not None:
            self.debug_match_fp.flush()

        if self.debug_input_points_fp is not None:
            self.debug_input_points_fp.flush()

    def log_cluster_points(self, timestamp, json_list, cid):
        """
        Method to log all the clustered points. The points will be appended
        to the cluster log file as indicated by the global variable
        "DEBUG_CLUSTER_FILE". If the "DEBUG_CLUSTER_FILE" is None, then the
        cluster points will not be logged.

        Each row has the following will have the comma-seprated columns:
        <key,timestamp,cid,x,y,cam,vehicle,objid,placeId>
        where
            a. key: This will always be the string "Cluster"
            b. timestamp: The timestep at which this cluster was formed
            c. cid: The cluster id
            d. x,y: The global x and y coordinate of the cluster
            e. cam: The camera where the point was detected
            f. vehicle: The vehicle string corresponding to the detection
            g. objid: The object id
            f. placeId: Place id

        Arguments:
            timestamp {[datetime]} -- The timestep at which this cluster was
            formed
            json_list {[list]} -- The list of day2 schema jsons that are
            present in the cluster
            cid {[int]} -- The cluster id of the cluster

        Returns: None
        """

        if self.debug_cluster_fp is not None:
            for rec in json_list:
                varx, vary = trackerutils.get_xy(rec)
                cam = trackerutils.get_camera(rec)
                veh_str = trackerutils.get_vehicle_string(rec)
                self.debug_cluster_fp.write(
                    "Cluster,{},{},{},{},{},{},{},{}\n".format(
                        timestamp, cid, varx, vary, cam, veh_str,
                        rec["object"]["id"], rec["place"]["id"]))

    def log_input_points(self, json_list, ignored_list, id_start):
        """
        Method to log all the input points that the tracker is receiving. The
        points will be appended to the input log file as indicated by the variable
        "DEBUG_INP_POINTS_FILE". If the "DEBUG_INP_POINTS_FILE" is None, then the
        input points will not be logged.

        Each row has the following will have the comma-seprated columns:
        <key,id,tsbin,timestamp,event,x,y,cam,vehicle,objid,placeId,ignored>
        where
            a. key: This will always be the string "Points"
            b. id: The id of the point
            c. tsbin: The timestep at which this point was observed
            d. timestamp: The exact timestamp at which this point was detected
            e. event: The type of detection event (moving, entry, exit, parked,
               pulled)
            f. x,y: The global x and y coordinate of the cluster
            g. cam: The camera where the point was detected
            h. vehicle: The vehicle string corresponding to the detection
            i. objid: The object id
            j. placeId: Place id
            k. ignored: Is the point ignored since the point was falls in a
               polygon that was marked to be ignored for that particular
               camera (as defined by config "IGNORE_DETECTION_DICT_MOVING")

        Arguments:
            json_list {[list]} -- The list of day2 schema jsons for the input
            points that are not igored by the tracker
            ignored_list {[list]} -- The list of day2 schema jsons for the
            ignored points
            id_start {[int]} -- the starting id for the points

        Returns:
            {[int]} -- The new id_start for the next batch of points
        """

        new_json_list = []
        for ele in json_list:
            new_ele = ele.copy()
            new_ele["ignored"] = 0
            new_json_list.append(new_ele)

        for ele in ignored_list:
            new_ele = ele.copy()
            new_ele["ignored"] = 1
            new_json_list.append(new_ele)

        time_indexed_json_dict = trackerutils.create_time_windows(
            new_json_list, self.resample_time_secs)

        for timestamp, all_json_list in time_indexed_json_dict.items():

            s_json_list = sorted(all_json_list, key=lambda k: k['@timestamp'])
            if self.debug_input_points_fp is not None:
                for rec in s_json_list:
                    varxy = trackerutils.get_xy(rec)
                    if varxy is not None:
                        varx = varxy[0]
                        vary = varxy[1]
                    else:
                        varx = 0
                        vary = 0

                    cam = trackerutils.get_camera(rec)
                    veh_str = trackerutils.get_vehicle_string(rec)
                    self.debug_input_points_fp.write(
                        "Points,{},{},{},{},{},{},{},{},{},{},{}\n".format(
                            id_start, timestamp, rec["@timestamp"],
                            rec["event"]["type"], varx, vary,
                            cam, veh_str, rec["object"]["id"],
                            rec["place"]["id"], rec["ignored"]))
            id_start += 1

        return id_start

    def log_match_points(self, timestamp1, json_ele1, timestamp2, json_ele2, match_id):
        """
        Method to log all the matched points. The tracker matches clusters at
        tiemstamp (t-1) with those at timestamp t. The points will be appended
        to the matching log file as indicated by the global variable
        "DEBUG_MATCH_FILE". If the "DEBUG_MATCH_FILE" is None, then the
        match points will not be logged.

        Each row has the following will have the comma-seprated columns that
        represents cluster at time (t-1) (points suffixed by "1") and time t
        (points suffixed by "2"):
        <
         key,timestamp1,timestamp2,match_id,x1,y1,cam1,veh1,objid1,placeid1,
         x2,y2,cam2,veh2,objid2,placeid2
        >
        where
            a. key: This will always be the string "Match"
            b. timestamp1: The timestamp of point at time (t-1) (Point 1)
            c. timestamp2: The timestamp of point at time (t) (Point 2)
            d. match_id: The match_id represents the timestamp at which these
               points are matched
            e. x1,y1: The global x and y coordinate of the Point 1
            f. cam1: The camera where the point 1 was detected
            g. veh1: The vehicle string corresponding to the detection of
               point 1
            h. objid1: The object id of point 1
            i. placeId1: Place id for point 1
            j. x2,y2: The global x and y coordinate of the Point 2
            k. cam2: The camera where the point 2 was detected
            l. veh2: The vehicle string corresponding to the detection of
               point 2
            m. objid2: The object id of point 2
            n. placeId2: Place id for point 2

        Arguments:
            timestamp1 {[datetime]} -- the timestep at which point 1 was detected
            json_ele1 {[dict]} -- The json element of point 1
            timestamp2 {[type]} -- the timestep at which point 2 was detected
            json_ele2 {[type]} -- The json element of point 2
            match_id {[type]} -- the match id
        """

        if self.debug_match_fp is not None:

            varx1 = ""
            vary1 = ""
            varx2 = ""
            vary2 = ""
            cam1 = ""
            cam2 = ""
            veh1 = ""
            veh2 = ""
            objid1 = ""
            objid2 = ""
            placeid1 = ""
            placeid2 = ""

            if json_ele1 is not None:
                varx1, vary1 = trackerutils.get_xy(json_ele1)
                cam1 = trackerutils.get_camera(json_ele1)
                veh1 = trackerutils.get_vehicle_string(json_ele1)
                objid1 = json_ele1["object"]["id"]
                placeid1 = json_ele1["place"]["id"]

            if json_ele2 is not None:
                varx2, vary2 = trackerutils.get_xy(json_ele2)
                cam2 = trackerutils.get_camera(json_ele2)
                veh2 = trackerutils.get_vehicle_string(json_ele2)
                objid2 = json_ele2["object"]["id"]
                placeid2 = json_ele2["place"]["id"]

            self.debug_match_fp.write("Match,{},{},{},{},{},{},{},{},{},{},{},{},"
                                      "{},{},{}\n".format(timestamp1, timestamp2,
                                                          match_id, varx1, vary1, cam1,
                                                          veh1, objid1, placeid1,
                                                          varx2, vary2, cam2, veh2,
                                                          objid2, placeid2))
