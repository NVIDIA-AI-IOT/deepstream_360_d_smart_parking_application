"""
This module has core classes for multicam tracking
"""

__version__ = '0.2'

import copy
import logging
import math

import iso8601
import numpy as np
import scipy.spatial.distance as ssd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import linear_sum_assignment
from scipy.spatial import distance_matrix
from shapely.geometry import LineString, Point

from mctrack import constants, trackerutils, tracklog
from geo.core import spatial
from euclidean import euchelper
from network import networkhelper


class MulticamTrackerConfig:
    """
    This class has the configuration for multicam tracking
    """

    def __init__(self, config):
        self.cl_dist_thresh_m = (config
                                 .get("CLUSTER_DIST_THRESH_IN_M",
                                      constants.DEF_CLUS_DIST_THRESH_M))
        self.match_max_dist_m = (config
                                 .get("MATCH_MAX_DIST_IN_M",
                                      constants.DEF_MATCH_MAX_DIST_IN_M))
        self.carry_time_sec = (config
                               .get("CARRY_OVER_LIST_PRUNE_TIME_IN_SEC",
                                    constants.DEF_CARRY_PRUNE_TIME_SEC))


class MulticamTrackerState:
    """
    This class takes care of preserving state of multi-cam tracker. This is
    needed for streaming systems which need to maintain state and then use it
    in consequent time-periods. Currently, the class preserves the state in
    an object. Few options for users to persist the state on disk:
    1. Store the object as a pickle
    2. Serialize and de-serialize this object as json: Convert this class
       variables to json, and persist the json
    """

    def __init__(self, config):
        """Init method

        Arguments:
            config [dict] -- A dictionary that has the following keys
                a. "overlappig_camera_ids": This key specifies the
                   cameras which have overlapping coverages. If this
                   dictionary has non-zero number of keys, then the tracker
                   will only merge detections from the overlapping cameras.
                   It will not merge between the cameras that do not overlap;
                   it will always be kept separate
                b. "conflict_cameras_adj_list": This key specifies the cameras
                   whose detections shoult NOT be merged together. For example,
                   there two objects detected from two neighboring cameras that
                   monitor entry and exit lanes are closeby in space. However,
                   since this lane is divided, we would not want the detections
                   from both cameras to be merged even though their detections
                   are closeby.
                c. "MAP_INFO": This key specifies the road-network information.
                   The road-network graph is represented as a set of lines. Each
                   line has a set of points [set of (lon, lat)]. This map will be
                   used to snap detected points to the road network if the option
                   if SNAP_POINTS_TO_GRAPH is True
                d. "IGNORE_DETECTION_DICT_MOVING": This dictionary value indicates
                   the polygons inside which detections has to be ignored (not
                   processed). For each camera, we can specify a list of polygons
                   where detections have to be ignored. Often there are regions
                   (ROIs) where the detections should be ignored. The reason for
                   ignoring may be since the user has defined only specific ROI to
                   ignore, or also may be because the detections in those regions
                   are prone to high false-detections (e.g., due to frequent
                   lighting changes)

        Returns: None
        """
        self.unidentified_cars = []
        self.prev_list = []
        self.prev_timestamp = None
        self.carry_over_list = []
        self.retval = []
        self.match_stats = []
        self.possible_parked_cars = []
        # STATE STORE: The below variables store the states of the tracking module
        self.parking_spot_state = {}

        self.curr_unknown_veh_id = 0
        self.match_id = 0

        self.overlappig_camera_ids = config.get("overlappig_camera_ids", None)
        self.map_info = config.get("MAP_INFO", None)
        self.conflict_cameras_adj_list = config.get(
            "conflict_cameras_adj_list", None)

        self.dense_map_info = None
        self.road_network = None

        self.clustered_oid_list = []
        self.clustered_oid_map = {}
        self.curr_cl_obj_id = 0

        if self.map_info is not None:
            self.dense_map_info = euchelper.densify_graph(self.map_info)
            self.road_network = networkhelper.Network(
                self.dense_map_info, max_point_dist=0.1)


class MulticamTracker:
    """
    Main multicamera tracking algorithm. The algorithm inputs and outputs list
    of jsons in day2 schema. The output list contains the tracked objects of
    the input list.

    The algorithm has three main components:
    1. Per-Camra Clustering: Aggregate multiple frames from the same camera
       that arrive within 0.5 second.
    2. Inter-Camera Clustering: Aggregate across cameras and transfer
       attributes
    3. Inter-Period Matching: Match across consecutive time-periods and
       transfer attributes
    """

    def __init__(self, config):
        """
        Init method

        Arguments:
            config [dict] -- A dictionary that has the following keys
                a. "overlappig_camera_ids": This key specifies the
                   cameras which have overlapping coverages. If this
                   dictionary has non-zero number of keys, then the tracker
                   will only merge detections from the overlapping cameras.
                   It will not merge between the cameras that do not overlap;
                   it will always be kept separate
                b. "conflict_cameras_adj_list": This key specifies the cameras
                   whose detections shoult NOT be merged together. For example,
                   there two objects detected from two neighboring cameras that
                   monitor entry and exit lanes are closeby in space. However,
                   since this lane is divided, we would not want the detections
                   from both cameras to be merged even though their detections
                   are closeby.
                c. "MAP_INFO": This key specifies the road-network information.
                   The road-network graph is represented as a set of lines. Each
                   line has a set of points [set of (lon, lat)]. This map will be
                   used to snap detected points to the road network if the option
                   if SNAP_POINTS_TO_GRAPH is True
                d. "IGNORE_DETECTION_DICT_MOVING": This dictionary value indicates
                   the polygons inside which detections has to be ignored (not
                   processed). For each camera, we can specify a list of polygons
                   where detections have to be ignored. Often there are regions
                   (ROIs) where the detections should be ignored. The reason for
                   ignoring may be since the user has defined only specific ROI to
                   ignore, or also may be because the detections in those regions
                   are prone to high false-detections (e.g., due to frequent
                   lighting changes)

        Returns: None
        """
        self.state = MulticamTrackerState(config)
        self.mclogger = tracklog.MulticamTrackLogger(config)
        self.config = MulticamTrackerConfig(config.get("trackerConfig", {}))

    def init_transforms(self, json_list):
        """
        This method is called as an init method before passing the day2 schema.
        Some of the work done by this method is:
        1. Change the object id as a combination of sensor id and object id
        2. If the detected object is a "vehicle", and if the license and
           licenseState is "None", then we convert them to empty strings
        3. If SNAP_POINTS_TO_GRAPH is True, then it will also change the (x,y)
           of each vehicle. The (x,y) will be snapped to the road-network edge.
           Snapping is done by projecting the original (x,y) to the nearest
           point on the nearest edge

        Arguments:
            json_list {[list]} -- [Transformed dictionaries of detections in day2 schema]
        """
        # Make obj id as sensor_id + obj id
        for json_ele in json_list:
            if ((json_ele.get("sensor", {}).get("id", None) is not None) and
                    (json_ele.get("object", {}).get("id", None) is not None)):

                json_ele["object"]["id"] = trackerutils.get_obj_id_in_sensor(
                    json_ele)
            if json_ele.get("object", {}).get("vehicle", None) is not None:
                veh = json_ele["object"]["vehicle"]
                if veh.get("license", None) is None:
                    veh["license"] = ""
                if veh.get("licenseState", None) is None:
                    veh["licenseState"] = ""

            # TODO: Temporary fix to make sure "level" is in uppercase
            aisle_rec = json_ele.get("place", {}).get("aisle", None)
            if aisle_rec is not None:
                aisle_rec["level"] = aisle_rec["level"].upper()
            spot_rec = json_ele.get("place", {}).get("parkingSpot", None)
            if spot_rec is not None:
                spot_rec["level"] = spot_rec["level"].upper()

        if constants.SNAP_POINTS_TO_GRAPH:
            self.match_moving_points_to_map(
                json_list, map_info=self.state.map_info)

    def match_point_to_map(self, json_ele, map_info):
        """
        This method matches the vehicle detection (argument "json_ele") to the
        road-network. The (x,y) will be snapped to the road-network edge.
        Snapping is done by projecting the original (x,y) to the nearest
        point on the nearest edge. Note that the json_ele is overwritten with
        the new (x,y) point on the road-network

        Arguments:
            json_ele {[dict]} -- [The day2 schema dict of the vehicle detection]
            map_info {[list]} -- [The road-network given as a list of line-strings]

        Returns: None. Note that the json_ele is overwritten with
        the new (x,y) point on the road-network.
        """
        varxy = trackerutils.get_xy(json_ele)
        if varxy is not None:
            min_line, min_dist, projected_pt = self.get_snap_pt(
                varxy, map_info)
            if min_line is not None and min_dist <= constants.MAX_DIST_SNAP_MAP:
                json_ele["object"]["coordinate"]["x"] = projected_pt[0]
                json_ele["object"]["coordinate"]["y"] = projected_pt[1]
                # -- logging.debug("\tJson ele: {}: Snapping pt  {} to {}"
                # .format(get_vehicle_string(json_ele), xy, projected_pt))

    def match_moving_points_to_map(self, json_list, map_info):
        """This method maps all points in the json_list to the nearest points
        on the map_info

        Arguments:
            json_list {[list]} -- The list of day2 schema dictionaries of
            vehicle detection
            map_info {[type]} -- road-network graph as a list of line-strings
        """
        map_info = np.array(map_info)
        if map_info is not None:
            for json_ele in json_list:
                if json_ele.get("event", {}).get("type", None) == "moving":
                    self.match_point_to_map(json_ele, map_info)

    # Clustering functions
    def merge_cluster_id_sets(self, merge_obj_id_list):
        """
        Method to merge all ids for a single cluster given that two or
        more ids (in merge_obj_id_list)

        Arguments:
            merge_obj_id_list {list} -- The set of objects for which the ids
                need to be merged
        """

        min_id = None
        uniq_obj_ids = set()
        max_ts = None
        logging.info("ID list: Merging for objects %s", str(merge_obj_id_list))
        for obj_id in merge_obj_id_list:
            this_dict = self.state.clustered_oid_map[obj_id]
            logging.info("ID list:\tOld: %s: %s", obj_id, str(this_dict))
            if min_id is None or this_dict["id"] < min_id:
                min_id = this_dict["id"]
                uniq_obj_ids.update(this_dict["id_set"])
            if max_ts is None or this_dict["update_ts"] > max_ts:
                max_ts = this_dict["update_ts"]

        new_dict = {
            "update_ts": max_ts,
            "id_set": uniq_obj_ids,
            "id": min_id
        }
        for obj_id in uniq_obj_ids:
            self.state.clustered_oid_map[obj_id] = new_dict

    def prune_cluster_id_sets(self, timestamp):
        """Prune cluster object ids which were updated long back. The time
        thershold is given by self.config.cluster_obj_id_staytime_in_sec

        Arguments:
            timestamp {datetime} -- current timestamp
        """

        obj_keys = list(self.state.clustered_oid_map.keys())
        for obj_id in obj_keys:
            this_ts = self.state.clustered_oid_map[obj_id]["update_ts"]
            delta_time = (timestamp - this_ts).total_seconds()
            if delta_time > constants.CLUSTERED_OBJ_ID_PRUNETIME_SEC:
                del self.state.clustered_oid_map[obj_id]

    def maintain_matched_ids(self, clustered_json_list):
        """Maintain the object ids of the clustered trajectories

        Arguments:
            clustered_json_list {list} -- list of detections in a single cluster
        """
        if clustered_json_list:

            # 1. Find a valid set across all elements
            first_obj_id = None
            same_id_list = None
            json_ele = None
            for json_ele in clustered_json_list:
                first_obj_id = trackerutils.get_obj_id(json_ele)
                same_id_list = self.state.clustered_oid_map.get(
                    first_obj_id, None)
                if same_id_list is not None:
                    break

            if same_id_list is None:
                # Create a new set with this obj id in it
                same_id_list = {
                    "update_ts": iso8601.parse_date(
                        json_ele.get("@timestamp")),
                    "id_set": set([first_obj_id]),
                    "id": self.state.curr_cl_obj_id
                }
                self.state.curr_cl_obj_id += 1
                self.state.clustered_oid_map[first_obj_id] = same_id_list

            set_id = same_id_list['id']
            curr_set = same_id_list['id_set']
            merge_sets = []
            for json_ele in clustered_json_list:
                obj_id = trackerutils.get_obj_id(json_ele)
                this_set_list = self.state.clustered_oid_map.get(
                    obj_id, None)
                this_ts = iso8601.parse_date(json_ele["@timestamp"])

                if this_set_list is None:

                    # This is a new object. Add it to the list
                    curr_set.add(obj_id)
                    self.state.clustered_oid_map[obj_id] = same_id_list
                else:

                    if ((this_set_list['id'] != set_id) or
                            (first_obj_id not in this_set_list['id_set'])):

                        # There is some problem. We see that two different
                        # ids have been issued for the same cluster elements
                        merge_sets.append(obj_id)

                if this_ts > same_id_list["update_ts"]:
                    same_id_list["update_ts"] = this_ts

            if merge_sets:
                self.merge_cluster_id_sets([first_obj_id] + merge_sets)


    def prune_nearby_points_in_list(self, timestamp, json_list, params):
        """
        This method clusters all points in the list (json_list). The method
        returns a list of points, where nearby points (in one cluster) have
        been collated into one representative point

        Arguments:
            timestamp {[type]} -- The timestep at which this clustering will
            be done
            json_list {[list]} -- The list of day2 schema dictionaries of
            vehicle detection
            params {dict} -- Dictionary parameters for clustering. It can have
            the following keys:
            a. "dist_thresh" key: indicates the distance threshold for
               clustering

            If "dist_thresh" key is not provided or if params is None, then
            "dist_thresh" for clustering defaults to CLUSTER_DIST_THRESH_IN_M
            in the config file or consants.DEFAULT_CLUSTER_DIST_THRESH_IN_M


        Returns:
            [list] -- list of points (in day2 schema dict) where points in each
            cluster has been collated into one representative point
        """
        json_list = self.collate_single_obj_attr(json_list)
        retval = json_list
        dist_thresh = (params
                       .get("dist_thresh", self.config.cl_dist_thresh_m)
                       if params is None else self.config.cl_dist_thresh_m)
        if len(json_list) > 1:
            retval = []
            cluster_assocs = self.get_cluster(
                json_list, dist_thresh, params)
            clusters = set(cluster_assocs)

            # data = []
            final_cid = 0
            # Create hash for clusters
            for k in clusters:
                # if k == -1:
                #     # Black used for noise.
                #     name = "Noise"
                # else:
                #     name = "Cluster_" + str(k)

                members = [i for i in range(
                    len(cluster_assocs)) if cluster_assocs[i] == k]

                name_list = []
                x_list = []
                y_list = []
                # num_cars = len(members)
                cluster_vehicles = set()
                cluster_cameras = set()
                for mem in members:
                    xy_coord = trackerutils.get_xy(json_list[mem])
                    cam_name = trackerutils.get_camera(json_list[mem])
                    veh_name = trackerutils.get_vehicle_string(json_list[mem])
                    point_name = veh_name + " : " + \
                        cam_name + " : " + str(xy_coord)
                    cluster_vehicles.add(veh_name)
                    cluster_cameras.add(cam_name)
                    name_list.append(point_name)
                    x_list.append(xy_coord[0])
                    y_list.append(xy_coord[1])

                rec_list = [json_list[i] for i in members]
                self.maintain_matched_ids(rec_list)
                # If points from more than one camera is in the same cluster, they are the same
                if len(cluster_cameras) > 1:

                    self.mclogger.log_cluster_points(timestamp, rec_list,
                                                     "C_{}".format(final_cid))
                    self.smooth_x_y_in_list(
                        rec_list, reason="Clustering points from multiple cameras")
                    self.xfer_attrb_for_1valid_veh(rec_list)
                    sel_rec = self.select_rep_member_from_list(
                        rec_list)  # rec_list[len(rec_list) - 1]
                    sel_rec["object"]["id_list"] = self.concatenate_member_ids(
                        rec_list)
                    retval.append(sel_rec)
                    final_cid += 1
                else:
                    # Points are from single camera. Send them as individual
                    # records
                    retval += rec_list
                    for i in members:
                        rec_list = [json_list[i]]
                        self.mclogger.log_cluster_points(timestamp, rec_list,
                                                         "C_{}".format(
                                                             final_cid))
                        final_cid += 1
                    # final_cid += len(members)

        elif len(json_list) == 1:
            self.mclogger.log_cluster_points(timestamp, json_list, "C_0")
        return retval

    def prune_nearby_points(self, timestamp, state_recs, params):
        """
        This method will cluster all nearby moving points. The following is
        done:
        1. The clustering of moving points is done by calling
        :func:`~reid.MulticamTracker.prune_nearby_points_in_list`
        2. All the parked records are clustered as "Parked" and logged

        Arguments:
            timestamp {[datetime]} -- The timestamp time-step at which the
            clustering is being done
            state_recs {[dict]} -- A list of day2 schema dictionary of
            detections. This dictionary will have moving points under the
            state_recs['moving']
            params {dict} -- Dictionary parameters for clustering. It can have
            the following keys:
            a. "dist_thresh" key: indicates the distance threshold for
               clustering

            If "dist_thresh" key is not provided or if params is None, then
            "dist_thresh" for clustering defaults to CLUSTER_DIST_THRESH_IN_M
            in the config file or consants.DEFAULT_CLUSTER_DIST_THRESH_IN_M

        Keyword Arguments:
            match_id {int} -- The id of the timestep at which this clustering
            is done (default: {0})

        Returns:
            [dict] -- the state_recs dictionary itself. Note that moving
            records in state_recs (state_recs['moving']) will be substituted
            with a single point for each cluster
        """
        # Merge points which were moving + newly parked
        moving_recs = state_recs['moving']
        state_recs['moving'] = self.prune_nearby_points_in_list(
            timestamp, moving_recs, params)
        self.mclogger.log_cluster_points(
            timestamp, state_recs['parked'], "Parked")
        return state_recs

    def smooth_x_y_in_list(self, rec_list, reason="No reason"):
        """
        This method replaces a vehicle detections in a list by a representative
        point (x,y). Currently, the logic is:
            computed (x,y) = (mean(x_i), mean(y_i)) for all (xi,yi) in rec_list

        All the records in the rec_list are updated with the new (x,y)
        computed. The original (xi, yi) are stored in
        rec['object']['coordinate']['origPoints']
        where rec is a dict in rec_list

        Arguments:
            rec_list {[list]} -- The list of day2 schema dictionaries of
            vehicle detection

        Keyword Arguments:
            reason {str} -- Used for logging so that we know why
            the points in the list were consolidated
            (default: {"No reason"})
        """
        rec_list = sorted(rec_list, key=lambda k: k['@timestamp'])


        # Different ways to pick the (x,y) from the list of points
        # pts = [(rec['object']['coordinate']['x'], rec['object']
        #        ['coordinate']['y']) for rec in rec_list]
        # 1. Mean,
        #x_rep, x_rep = trackutils.get_median_xy(pts)
        # 2. Mean
        #x_rep, x_rep = trackutils.get_mean_xy(pts)
        # 3. Find the point that is nearest to the camera. In the 360-d usecase,
        # this is the point with highest camera_y coordinate
        pts = [(rec['object']['coordinate']['x'],
                rec['object']['coordinate']['y'],
                (rec['object']['bbox']['topleftx'] +
                 rec['object']['bbox']['bottomrightx'])/2.0,
                max(rec['object']['bbox']['toplefty'],
                    rec['object']['bbox']['bottomrighty']),
                ) for rec in rec_list]
        x_rep, y_rep = trackerutils.get_max_camy_xy(pts)

        for rec in rec_list:
            if rec['object']['coordinate'].get('origPoints', None) is None:
                rec['object']['coordinate']['origPoints'] = []
            rec['object']['coordinate']['origPoints'].append({
                "x": rec['object']['coordinate']['x'],
                "y": rec['object']['coordinate']['y'],
                "reason": reason
            })
            # rec['object']['coordinate']['orig_y'] = rec['object']['coordinate']['y']
            rec['object']['coordinate']['x'] = x_rep
            rec['object']['coordinate']['y'] = y_rep

    def select_rep_member_from_list(self, json_list):
        """
        This method selects one representative dict from the list
        of vehicle detections (in json_list)

        Returns:
            [dict] -- A representative day2 schema dictionary of
            selected representative vehicle detection
        """
        retval = None
        if json_list:
            retval = json_list[0]
            pref = 100
            min_obj_id = None
            for ele in json_list:
                # 1st pref = entry/exit
                # 2nd pref = one with videopath
                if ele["event"]["type"] in ["entry", "exit"]:
                    retval = ele
                    pref = 1
                elif(pref > 1) and (ele["videoPath"] != ""):
                    retval = ele
                    pref = 2
                elif(pref > 2) and (min_obj_id is None or
                                    min_obj_id > ele["object"]["id"]):
                    retval = ele
                    min_obj_id = ele["object"]["id"]
                    pref = 3
        return retval

    def get_cluster(self, json_list, max_d, params):
        """
        This method clusters all vehicle detections in the json_list. Currently
        it:
        1. computes distance matrix between vehicle detections
        2. hierarchical aggregation
        3. Cuts the dendrogram at max_d

        Arguments:
            json_list {[list]} -- The list of day2 schema dictionaries of
            vehicle detection
            max_d {[double]} -- The cut-off distance. This variable is passed
            to fcluster with criterion="distance"
            params {[type]} -- Parameters required for clustering vehicle
            detections. Key parameters include:
            a. cam_overlap_adj_list: A adjacency list of which cameras
                have overlap with which other cameras. This is computed
                based on the "overlappig_camera_ids" key in the config dict
                passed to MulticamTracker. This key specifies the
                cameras which have overlapping coverages. If this
                dictionary has non-zero number of keys, then the tracker
                will only merge detections from the overlapping cameras.
                It will not merge between the cameras that do not overlap;
                it will always be kept separate
            b. conflict_cameras_adj_list: This key specifies the cameras
                whose detections shoult NOT be merged together. For example,
                there two objects detected from two neighboring cameras that
                monitor entry and exit lanes are closeby in space. However,
                since this lane is divided, we would not want the detections
                from both cameras to be merged even though their detections
                are closeby.

        Returns:
            [list] -- Cluster number of each of points in json_list
        """
        dist_matrix = self.get_distance_matrix(json_list, json_list)
        rows = cols = dist_matrix.shape[0]
        for i in range(0, rows):
            for j in range(i + 1, cols):

                if constants.ASSUME_OBJS_HAVE_SAME_ID_INTRA_FRAME_PERIOD:
                    # If two objects have been assigned same id in the past,
                    # then distance = 0
                    obj_1_id = trackerutils.get_obj_id(json_list[i])
                    obj_2_id = trackerutils.get_obj_id(json_list[j])
                    obj_1_set = (self.state
                                 .clustered_oid_map.get(obj_1_id, {})
                                 .get("id_set", set()))
                    obj_2_set = (self.state
                                 .clustered_oid_map.get(obj_2_id, {})
                                 .get("id_set", set()))
                    if obj_1_id in obj_2_set or obj_2_id in obj_1_set:
                        dist_matrix[i][j] = dist_matrix[j][i] = 0.0

                if ((trackerutils.get_camera(json_list[i]) ==
                     trackerutils.get_camera(json_list[j])) or
                        (not self.cameras_overlap(
                            json_list[i], json_list[j], params)) or
                        (self.conflict_cameras(
                            json_list[i], json_list[j], params))):

                    # Non-overlapping cameras. Dist is inf
                    dist_matrix[i][j] = dist_matrix[j][i] = max_d * \
                        constants.CLUSTER_DIFFT_CAMERAS_LARGE_SCALE_FACTOR

        dist_array = ssd.squareform(dist_matrix)
        z_val = linkage(dist_array, 'complete')
        clusters = fcluster(z_val, max_d, criterion='distance')
        return clusters

    def cluster_recs_from_same_cam(self, json_list):
        """
        Each camera may have multiple frames within a given resample period.
        In such cases, single object may be detected multiple times. If
        multiple detections of same object is present, it becomes harder to
        track. This method will keep a single detection of the object per
        resample period

        Returns:
            [list] -- List of day2 schema based dictionaries of
            non-replicated detections from each camera per resample
            period
        """

        if len(json_list) > 1:
            dist_matrix = self.get_distance_matrix(json_list, json_list)
            rows = cols = dist_matrix.shape[0]
            for i in range(0, rows):
                for j in range(i + 1, cols):
                    if json_list[i]["object"]["id"] == json_list[i]["object"]["id"]:
                        # Same id (within same frame or across frames)
                        dist_matrix[i][j] = dist_matrix[j][i] = 0
                    elif((json_list[i]["@timestamp"] ==
                          json_list[i]["@timestamp"]) and
                         (json_list[i]["object"]["id"]
                          != json_list[i]["object"]["id"])):
                        # Same timestamp(frame) and different ids
                        if not constants.MERGE_CLOSE_BBS_FROM_SAME_CAM:
                            # Dist is inf
                            dist_matrix[i][j] = dist_matrix[j][i] = (
                                constants.INTRA_FRAME_PERIOD_CLUST_DIST_IN_M *
                                constants.INTRA_FRAME_CLUSTER_LARGE_SCALE_FACTOR)

            dist_array = ssd.squareform(dist_matrix)
            z_val = linkage(dist_array, 'complete')
            cluster_assocs = fcluster(
                z_val, constants.INTRA_FRAME_PERIOD_CLUST_DIST_IN_M,
                criterion='distance')
            clusters = set(cluster_assocs)
            retval = []
            for k in clusters:
                members = [i for i in range(
                    len(cluster_assocs)) if cluster_assocs[i] == k]
                member_recs = [json_list[i] for i in members]
                if len(member_recs) > 1:
                    diff_id_list = [rec["object"]["id"]
                                    for rec in member_recs]
                    diff_id_set = set(diff_id_list)
                    if len(diff_id_set) > 1:
                        logging.warning("SameCamFrameCluster: Double detects?: %s",
                                      diff_id_list)
                    # Do not smooth xy. we need it for compiuting directions
                    # Do not transfer attributes. Just assign same object id
                    sel_rec = self.select_rep_member_from_list(member_recs)
                    for rec in member_recs:
                        rec["object"]["id"] = sel_rec["object"]["id"]


                retval += member_recs
        else:
            retval = json_list
        return retval

    # Matching functions
    def normalize_dist(self, xy_list, dist_norm_parameters):
        """This method normalizes the distance between an array of
         (x,y) points based on the minimum x,y and range of x,y.
         Specifically,
         normalized x = (x - xmin) / xrange
         normalized y = (y - ymin) / yrange

        Arguments:
            xy_list {[list]} -- List of (x,y) points
            dist_norm_parameters {[dict]} -- Parameters for normalization. It
            conatins the float values for the following keys:
            a. "minx": minimum of x
            b. "miny": minimum of y
            c. "xrange": range of x
            d. "yrange": range of y

        Returns:
            [list] -- List of normalized (x,y) points
        """
        minx = (dist_norm_parameters
                .get("minx", constants.DEFAULT_DIST_NORM_MINX)
                if dist_norm_parameters is not None
                else constants.DEFAULT_DIST_NORM_MINX)
        miny = (dist_norm_parameters
                .get("miny", constants.DEFAULT_DIST_NORM_MINY)
                if dist_norm_parameters is not None
                else constants.DEFAULT_DIST_NORM_MINY)
        rangex = (dist_norm_parameters
                  .get("xrange", constants.DEFAULT_DIST_NORM_XRANGE)
                  if dist_norm_parameters is not None
                  else constants.DEFAULT_DIST_NORM_XRANGE)
        rangey = (dist_norm_parameters
                  .get("yrange", constants.DEFAULT_DIST_NORM_YRANGE)
                  if dist_norm_parameters is not None
                  else constants.DEFAULT_DIST_NORM_YRANGE)

        return [((xy[0] - minx) / float(rangex),
                 (xy[1] - miny) / float(rangey))
                for xy in xy_list]

    def merge_costs(self, dist_matrix, id_dist_matrix):
        """
        This method inputs two distance matrices:
        a. spatial distance matrix (dist_matrix): This is a matrix with
           distances between two detections (nxn matrix for n detections)
        b. ID distance matrix (id_dist_matrix): This is a nxn matrix of 0s
           and 1s. If two detections i and j have the same id (e.g., single
           camera tracker id for the same camera), then the ixj th cell is
           set to 1. Else it is set to 0

        The output is also an nxn matrix where the distance is the spatial
        distance only if the IDs are different. If IDs are the same, then
        the distance is set to zero

        Special case: If either dist_matrix or id_dist_matrix is None, then
        the method returns dist_matrix

        Arguments:
            dist_matrix {[np.array]} -- Spatial distance matrix
            id_dist_matrix {[np.array]} -- ID distance matrix

        Returns:
            [np.array] -- Merged distance matrix
        """

        if dist_matrix is not None and id_dist_matrix is not None:
            assert dist_matrix.shape == id_dist_matrix.shape
            cost_matrix = dist_matrix.copy()
            for i in range(dist_matrix.shape[0]):
                for j in range(dist_matrix.shape[1]):
                    cost_matrix[i, j] = cost_matrix[i, j] * \
                        id_dist_matrix[i, j]
                    # if(id_dist_matrix[i, j] == 0):
                    #    cost_matrix[i, j] = 0.0
        else:
            # -- logging.debug("Dist or id matrix is none: DM={}, IDM={}".format(
            # --     dist_matrix, id_dist_matrix))
            cost_matrix = dist_matrix
        return cost_matrix

    def get_distance_matrix(self, prev_json_list, json_list,
                            dist_norm_parameters=None):
        """
        This method computes the eucledian distance between the detections at
        timestep (t-1) (indicated by prev_json_list) and detetions at
        timestep (t) (json_list). The x,y distances may be normalied by
        providing appropriate min and range values in dist_norm_parameters.

        Arguments:
            prev_json_list {[list]} -- List of day2 schema based dictionaries
            for detections at timestep (t-1).
            json_list {[list]} -- List of day2 schema based dictionaries
            for detections at timestep (t).

        Keyword Arguments:
            dist_norm_parameters {dict} -- Parameters for normalization. It
            conatins the float values for the following keys:
            a. "minx": minimum of x
            b. "miny": minimum of y
            c. "xrange": range of x
            d. "yrange": range of y
            (default: None)

        Returns:
            [np.array] -- Spatial distance matrix
        """

        xy1 = [trackerutils.get_xy(json_ele) for json_ele in prev_json_list]
        xy1 = self.normalize_dist(xy1, dist_norm_parameters)
        xy2 = [trackerutils.get_xy(json_ele) for json_ele in json_list]
        xy2 = self.normalize_dist(xy2, dist_norm_parameters)
        dist_matrix = distance_matrix(xy1, xy2)
        return dist_matrix

    def get_obj_id_dist_matrix(self, prev_json_list, json_list):
        """
        This method computes the ID distance between the detections at
        timestep (t-1) (indicated by prev_json_list) and detetions at
        timestep (t) (json_list). The x,y distances may be normalied by
        providing appropriate min and range values in dist_norm_parameters.

        The output is an nxn matrix where the distance is 1 if the IDs
        are different. If IDs are the same, then the distance is set to zero

        Note that an object might have multiple ids (e.g., two cameras
        might have detected same cars, and we might have clsutered them).
        In such cases, even if one id in one list matches with any id in
        other list, we set the value to 0.

        Arguments:
            prev_json_list {[list]} -- List of day2 schema based dictionaries
            for detections at timestep (t-1).
            json_list {[list]} -- List of day2 schema based dictionaries
            for detections at timestep (t).

        Returns:
            [np.array] -- ID distance matrix
        """

        id1 = [self.get_id_list(json_ele) for json_ele in prev_json_list]
        id2 = [self.get_id_list(json_ele) for json_ele in json_list]

        dist_matrix = np.ones((len(id1), len(id2)), dtype=np.int)

        for i in range(len(id1)):
            iset = set(id1[i])
            for j in range(len(id2)):
                jset = set(id2[j])
                int_set = iset.intersection(jset)
                # If there is at-least one id common in both
                if int_set:
                    dist_matrix[i, j] = 0.0
        return dist_matrix

    def match_points(self, prev_json_list, json_list, prev_timestamp,
                     timestamp, params, match_id=0):
        """
        This is the main matching function that matches detections at
        timestep (t-1) (prev_json_list) with detections at timestep (t)
        (json_list).

        Arguments:
            prev_json_list {[list]} -- List of day2 schema based dictionaries
            for detections at timestep (t-1).
            json_list {[list]} -- List of day2 schema based dictionaries
            for detections at timestep (t).
            prev_timestamp {[datetime]} -- Timestamp  @ timestep (t-1)
            timestamp {[datetime]} -- Timestamp  @ timestep (t)
            params {dict} -- Parameters for matching

        Keyword Arguments:
            match_id {int} -- The id of the matching step (default: {0})


        Returns:
            [dict] -- Returns a dictionary with the following keys:
                "assignedListIndicies": An array of integers pointing to the
                    detections in json_list
                "assignedPrevListIndicies": An array of integers pointing to
                    the detections in prev_json_list
                "unassignedPrevListIndicies": The indicies in prev_json_list
                    which are not matched to any point
                "unassignedListIndicies": The indicies in json_list
                    which are not matched to any point
                "carryOver": List of indicies from json_list which should be
                    carried over to the next timestep
                "stats": Statistics of matching
        """

        num_rows = len(prev_json_list)
        num_cols = len(json_list)
        unassigned_row_indicies = set(range(num_rows))
        unassigned_col_indicies = set(range(num_cols))
        carry_over_list = []
        match_stats = []
        assigned = []
        assigned_prev = []
        # -- logging.debug("\tMatching={},{}".format(num_rows, num_cols))
        if num_rows > 0 and num_cols > 0:
            dist_matrix = self.get_distance_matrix(prev_json_list, json_list)
            # -- logging.debug("\tDist Matrix={}".format(dist_matrix))
            id_dist_matrix = self.get_obj_id_dist_matrix(
                prev_json_list, json_list)
            # -- logging.debug("\tID Dist Matrix={}".format(id_dist_matrix))
            cost_matrix = self.merge_costs(dist_matrix, id_dist_matrix)
            # -- logging.debug("\tCost Matrix={}".format(cost_matrix))

            # Infeasible matchings (all distances more than 'x',
            # conflicting cameras) should be removed
            max_val = max(cost_matrix.max(),
                          self.config.match_max_dist_m * 1.1)
            # -- logging.debug("\tMax val={} (matrix max={})".format(
            # --     max_val, cost_matrix.max()))
            for i in range(cost_matrix.shape[0]):
                for j in range(cost_matrix.shape[1]):
                    if cost_matrix[i][j] > self.config.match_max_dist_m:
                        cost_matrix[i][j] = max_val
                    if self.conflict_cameras(prev_json_list[i],
                                             json_list[j], params):

                        # -- logging.debug("Not matching: Conflicting "
                        # "cameras: {}: {}: {}:{}".format(get_camera(
                        # prev_json_list[i]), get_camera(json_list[j]),
                        # i, j))
                        cost_matrix[i][j] = max_val
            # -- logging.debug(
            # --     "\tAfter constraints: Cost Matrix={}".format(cost_matrix))
            final_dist_matrix = copy.deepcopy(cost_matrix)
            cost_matrix = np.square(cost_matrix)
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            # -- logging.debug("\tMatching indicies: {} : {}".format(
            # row_ind, col_ind))

            # Take away all matchings which exceeds certain distance
            i = 0
            while i < row_ind.shape[0]:
                # xy1 = trackerutils.get_xy(prev_json_list[row_ind[i]])
                # xy2 = trackerutils.get_xy(json_list[col_ind[i]])
                # dist = spatialhelper.get_euc_dist(xy1, xy2)
                if (final_dist_matrix[row_ind[i]][col_ind[i]] >
                        self.config.match_max_dist_m):
                    row_ind = np.delete(row_ind, i)
                    col_ind = np.delete(col_ind, i)
                    # -- logging.debug("\t\t{}: Deleting index {}: dist={}:"
                    # -- " {} {}: row_ind={} col_ind={}".format(
                    # --     match_id, i, dist, xy1, xy2, row_ind, col_ind))
                else:
                    i += 1
                    # -- logging.debug("\t\t{}: Not deleting {}: dist={}: "
                    # -- "{}: {}".format(
                    # -- match_id, i, dist, xy1, xy2))

            for i in range(len(row_ind)):
                # -- logging.debug(
                # -- "DIFFT-TIME MATCHING: Transferring attributes [{}]: {}"
                # -- .format(i, len(json_list)))
                self.xfer_attrb_for_1valid_veh(
                    [prev_json_list[row_ind[i]], json_list[col_ind[i]]])
                self.mclogger.log_match_points(
                    prev_timestamp, prev_json_list[row_ind[i]], timestamp,
                    json_list[col_ind[i]], match_id)
                direction = self.get_direction(
                    prev_json_list[row_ind[i]], json_list[col_ind[i]],
                    dist_thresh=0)
                self.update_direction(json_list[col_ind[i]], direction)

                if trackerutils.is_parked_rec(json_list[col_ind[i]]):
                    # -- logging.debug("\t\tMatched aisle to a parked car: "
                    # -- "{}:{}:{} --> {}:{}:{}".format(
                    # --     prev_json_list[row_ind[i]]['object']['id'],
                    # --     get_camera(
                    # --         prev_json_list[row_ind[i]]),
                    # --     get_vehicle_string(prev_json_list[row_ind[i]]),
                    # --     json_list[col_ind[i]]['object']['id'],
                    # --     get_camera(json_list[col_ind[i]]),
                    # --     get_vehicle_string(json_list[col_ind[i]])))
                    pass

                if trackerutils.is_parked_rec(prev_json_list[row_ind[i]]):
                    # -- logging.debug("\t\tOOPS: Prev list contains a parked "
                    # -- "car and it got matched: {}-{}".format(
                    # --     get_vehicle_string(prev_json_list[row_ind[i]]),
                    # --     get_vehicle_string(json_list[col_ind[i]])))
                    pass

            for i in range(len(row_ind)):
                vehicle_t_1 = trackerutils.get_vehicle_string(
                    prev_json_list[row_ind[i]])
                vehicle_t_0 = trackerutils.get_vehicle_string(
                    json_list[col_ind[i]])
                unassigned_row_indicies.remove(row_ind[i])
                unassigned_col_indicies.remove(col_ind[i])
                assigned.append(col_ind[i])
                assigned_prev.append(row_ind[i])
                error = 0 if (vehicle_t_0 == vehicle_t_1) else 1
                (varx1, vary1) = trackerutils.get_xy(
                    prev_json_list[row_ind[i]])
                (varx2, vary2) = trackerutils.get_xy(json_list[col_ind[i]])
                match_stats.append(
                    {"matchId": match_id,
                     "index": i,
                     "isError": error,
                     "rowInd": row_ind[i], "colInd": col_ind[i],
                     "vehicle1": vehicle_t_1,
                     "time1": prev_json_list[row_ind[i]]['@timestamp'],
                     "x1": varx1, "y1": vary1, "x2": varx2, "y2": vary2,
                     "cam1": trackerutils.get_camera(
                         prev_json_list[row_ind[i]]),
                     "cam2": trackerutils.get_camera(
                         json_list[col_ind[i]]),
                     "vehicle2": vehicle_t_0,
                     "time2": json_list[col_ind[i]]['@timestamp']})

        else:
            if num_rows <= 0 and num_cols > 0:
                # -- logging.debug("\tMatching: Something arrived into a "
                # -- "camera view. Nothing to match to: #={}; {}".format(
                # --     len(json_list), json_list))
                pass
            elif num_cols <= 0 and num_rows > 0:
                # -- logging.debug("\tMatching: Something departed from a "
                # -- "camera view. Nothing to match to: #={}; {}".format(
                # --    len(prev_json_list),
                # --    prev_json_list))

                carry_over_list += prev_json_list.copy()

            elif num_cols == 0 and num_rows == 0:
                # -- logging.debug(
                # --     "\tMatching: Nothing arrived/departed into a camera "
                # --     "view. Nothing to match")
                pass
            else:
                # -- logging.debug(
                # --     "\tMatching: Something/Nothing arrived/departed. "
                # --     "Nothing to match to: {}: {}".format(prev_json_list,
                # --     json_list))
                pass

        for i in unassigned_row_indicies:
            self.mclogger.log_match_points(
                prev_timestamp, prev_json_list[i], timestamp, None, match_id)

            if trackerutils.is_parked_rec(prev_json_list[i]):
                    # -- logging.debug("\t\tOops: Non-matched parked car in "
                    # --     "prev json: {}:{}:{}".format(
                    # --     prev_json_list[i]['object']['id'], get_camera(
                    # --         prev_json_list[i]),
                    # --     get_vehicle_string(prev_json_list[i])))
                pass
            else:
                # For now do not carry over parking spot records
                carry_over_list.append(prev_json_list[i])

        for i in unassigned_col_indicies:
            self.mclogger.log_match_points(prev_timestamp, None, timestamp,
                                           json_list[i], match_id)
            # carry_over_list.append(json_list[i])
            if trackerutils.is_parked_rec(json_list[i]):
                # -- logging.debug("\t\tOops: Non-matched parked car in json:"
                # --     " {}:{}:{}".format(
                # --     json_list[i]['object']['id'], get_camera(json_list[i]),
                # --     get_vehicle_string(json_list[i])))
                pass

        return {"assignedListIndicies": assigned,
                "assignedPrevListIndicies": assigned_prev,
                "unassignedPrevListIndicies": unassigned_row_indicies,
                "unassignedListIndicies": unassigned_col_indicies,
                "carryOver": carry_over_list,
                "stats": match_stats}

    # Util functions
    def get_id_list(self, json_ele):
        """Get the list of ids associated with a given detection

        Arguments:
            json_ele {[dict]} -- Day2 schema dictionary

        Returns:
            [list] -- List of string IDs
        """
        return json_ele["object"].get("id_list", [json_ele["object"]["id"]])

    def xfer_attr_from_1vehicle(self, act_record, json_list):
        """
        Transfer vehicle attributes such as license plate, make, color
        from one record (act_record) to all the records in the list
        (json_list)


        Arguments:
            act_record {[dict]} -- Record from which the attribute need to be
            transfered
            json_list {[list]} -- List of records to which the records needs
            to be transferred to
        """
        for rec in json_list:
            if rec != act_record:
                rec['object']['vehicle'] = act_record['object']['vehicle'].copy()
                rec['object']['id'] = act_record['object']['id']

    def xfer_attrb_for_1valid_veh(self, json_list):
        """
        Transfer vehicle attributes such as license plate, make, color
        from one representative record to all the records in the list
        (json_list)

        Arguments:
            json_list {[type]} --  List of records where the attributes have
            to be the same
        """
        vindex = 0
        valid_vehicle = {}
        if json_list:
            for rec in json_list:
                key = trackerutils.get_vehicle_string(rec)
                if key != constants.UNK_VEH_KEY_STR_FORMAT:
                    if valid_vehicle.get(key, None) is None:
                        valid_vehicle[key] = [rec]
                    else:
                        valid_vehicle[key].append(rec)
                vindex += 1

            if len(valid_vehicle) > 1:
                # -- logging.warning("TRANSFER NOT DONE: Num valid vehicles
                # -- seem to be more than one! list={} valid_vehicles={}"
                # -- .format(
                # --     json_list, valid_vehicle.keys()))
                pass
            else:
                if len(valid_vehicle) == 1:
                    act_record = None
                    for i in valid_vehicle:
                        act_record = valid_vehicle[i][0]
                else:
                    act_record = json_list[0]
                    # add_synthetic_attributes_if_necessary([act_record])

                self.xfer_attr_from_1vehicle(
                    act_record, json_list)

    def collate_single_obj_attr(self, json_list):
        """
        This method collates objects of same tracker id
        and from the same sensor into a single object

        Arguments:
            json_list {[list]} -- List of day2 schema based dictionaries
            for detections

        Returns:
            [list] -- List of day2 schema based dictionaries
            for detections with same objects having same attributes
        """
        obj_in_cam_list = {}
        # 1. First detect if two objects have been detected too close within the camera
        for rec in json_list:
            cam_id = rec['sensor']['id']
            key = cam_id
            curr_obj_rec = obj_in_cam_list.get(key, None)
            if curr_obj_rec is None:
                # This is the first
                obj_in_cam_list[key] = [rec]
            else:
                obj_in_cam_list[key].append(rec)

        new_json_list = []
        for key in obj_in_cam_list:
            recs = obj_in_cam_list[key]
            # Cluster with very small threshold
            recs = self.cluster_recs_from_same_cam(
                recs)
            new_json_list += recs
        json_list = new_json_list

        # 2. Now single-camera tracker has put a tracker for each object. Use that
        obj_in_cam_list = {}
        for rec in json_list:
            cam_id = rec['sensor']['id']
            obj_id = ""
            if constants.ASSUME_OBJS_HAVE_SAME_ID_INTRA_FRAME_PERIOD:
                obj_id = rec['object']['id']

            key = cam_id + "__" + obj_id
            curr_obj_rec = obj_in_cam_list.get(key, None)
            if curr_obj_rec is None:
                # This is the first
                obj_in_cam_list[key] = [rec]
            else:
                obj_in_cam_list[key].append(rec)



        if constants.TAKE_ONE_FRAME_PER_PERIOD:
            new_json_list = []
            for key in obj_in_cam_list:
                recs = obj_in_cam_list[key]
                if (recs is not None) and recs:
                    new_json_list.append(recs[len(recs) - 1])
            json_list = new_json_list


            # Now re-key the records after transferring the attributes
            obj_in_cam_list = {}
            for rec in json_list:
                cam_id = rec['sensor']['id']
                obj_id = rec['object']['id']
                key = cam_id + "__" + obj_id
                curr_obj_rec = obj_in_cam_list.get(key, None)
                if curr_obj_rec is None:
                    # This is the first
                    obj_in_cam_list[key] = [rec]
                else:
                    obj_in_cam_list[key].append(rec)
        retval = []
        for key in obj_in_cam_list:
            rec_list = obj_in_cam_list[key]
            if rec_list:
                if len(rec_list) > 1:
                    # Get direction if more than one point
                    rec_list = sorted(rec_list, key=lambda k: k['@timestamp'])
                    rec = rec_list[0]
                    first_pt = (rec['object']['coordinate']['x'],
                                rec['object']['coordinate']['y'])
                    last_rec = rec_list[len(rec_list) - 1]
                    last_pt = (last_rec['object']['coordinate']
                               ['x'], last_rec['object']['coordinate']['y'])
                    self.smooth_x_y_in_list(
                        rec_list, reason="Collating multiple points within frame time period")

                    # Compute direction only if dist beween two points is more than x
                    dist_in_m = spatial.get_euc_dist(first_pt, last_pt)

                    if dist_in_m > constants.MIN_THRESHOLD_DIST_IN_M_WITHIN_RESAMPLE_TIME:
                        orientation_rad = spatial.get_radangle_flat_earth(
                            first_pt, last_pt)
                        orientation = math.degrees(orientation_rad)
                        last_rec['object']['direction'] = orientation
                        last_rec['object']['orientation'] = orientation

                    logging.debug(
                        "SAME TIME-CAM-OBJ: Transferring attributes: %d", len(rec_list))
                    self.xfer_attrb_for_1valid_veh(rec_list)
                retval.append(rec_list[len(rec_list) - 1])
        return retval

    def conflict_cameras(self, ele1, ele2, params):
        """
        Returns if two detections are from conflicting cameras or not

        Arguments:
            ele1 {[dict]} -- first detection (in day2 schema)
            ele2 {[dict]} -- first detection (in day2 schema)
            params {[dict]} -- A dictionary that has the following keys
                a. "conflict_cameras_adj_list": This key specifies the cameras
                   whose detections shoult NOT be merged together. For example,
                   there two objects detected from two neighboring cameras that
                   monitor entry and exit lanes are closeby in space. However,
                   since this lane is divided, we would not want the detections
                   from both cameras to be merged even though their detections
                   are closeby.

        Returns:
            [boolean] -- True if two detections are from conflicting cameras.
            False otherwise
        """
        cam_overlap_adj_list = params.get('conflict_cameras_adj_list', None)

        retval = False
        cam1 = trackerutils.get_camera(ele1)
        cam2 = trackerutils.get_camera(ele2)
        cam_list = cam_overlap_adj_list.get(cam1, None)
        cam_list2 = cam_overlap_adj_list.get(cam2, None)

        # We are assuming the graph is bidirectional and edge is listed in adj
        # list of either of the ends
        if (cam_list is not None) and (cam2 in cam_list):
            retval = True
        else:
            if((cam_list2 is not None) and
               (cam1 in cam_list2)):
                retval = True
        return retval

    def get_snap_pt(self, point, map_info):
        """
        Given a point (argument "point") and road_network, return the nearest
        point to given "point" on road-network
        Arguments:
            point {[tuple]} -- (x,y) of the point
            map_info {[list]} --
                   The road-network graph is represented as a set of lines.
                   Each line has a set of points [set of (x, y)]. This map
                   will be used to snap detected points to the road network
                   if the option if SNAP_POINTS_TO_GRAPH is True

        Returns:
            [tuple] -- Returns a tuple of three elements
            (min_line, min_dist, min_projected_pt)
            where min_line = the line to which the point was nearest
            min_dist = minimum distance from point to the line
            min_projected_pt = Projected point on the line
        """
        point = Point(point[0], point[1])
        min_dist = np.inf
        min_line = None
        min_projected_pt = None
        for orig_line in map_info:
            line = LineString(orig_line)
            line_projection = line.project(point)
            projected_pt = line.interpolate(line_projection)
            dist = point.distance(line)
            # -- logging.debug("\t\tPt to line: {} to {}. Dist = {}; "
            # -- "projection={}; projected_pt={}".format(pt,
            # -- list(line.coords), d, line_projection, projected_pt))
            if dist < min_dist:
                min_dist = dist
                min_line = orig_line
                min_projected_pt = list(projected_pt.coords)[0]

        # -- logging.debug("\tMin line. {} to {}. Min Dist = {}; "
        # -- "Projected Pt = {}".format(pt, min_line, min_dist,
        # -- min_projected_pt))
        return min_line, min_dist, min_projected_pt

    def get_vehicles_in_difft_states(self, json_list):
        """
        This method parses the json_list and categorizes them into four types
        of records based on the event observed.
        a. Parked records
        b. Empty records: When a parking spot goes empty
        c. Moving records: For moving cars
        d. Other records: None of the above

        Arguments:
            json_list {[list]} -- List of day2 schema based dictionaries
            for detections

        Returns:
            [dict] -- Dictionary with the keys:
            "parked", "emptySpots", "moving", "others"
            The value is the list of dictionaries (in day2 schema) under
            each category
        """
        parked_cars = []
        empty_spots = []
        moving_cars = []
        other_recs = []
        for json_ele in json_list:
            if trackerutils.is_spot_rec(json_ele):
                if json_ele.get("event", {}).get("type", None) == "parked":
                    parked_cars.append(json_ele)
                elif json_ele.get("event", {}).get("type", None) == "empty":
                    empty_spots.append(json_ele)
                else:
                    # -- logging.warning(
                    # --     "Parked car warning: The record is a parking spot"
                    # --  " record. However, it does not state if: (a) a car "
                    # --  "is parked or, (b) a spot is empty.\n Rec: {}"
                    # --  .format(json_ele))
                    pass
            elif trackerutils.is_aisle_rec(json_ele):
                moving_cars.append(json_ele)
            else:
                other_recs.append(json_ele)
                # -- logging.warning(
                # --     "Unknown movement: The record is neither a car in "
                # --     "spot or aisle.\n Rec: {}".format(json_ele))
        return {"parked": parked_cars,
                "emptySpots": empty_spots,
                "moving": moving_cars,
                "others": other_recs}

    def cameras_overlap(self, ele1, ele2, params):
        """
        Returns if two detections are from overlapping cameras or not

        Arguments:
            ele1 {[dict]} -- first detection (in day2 schema)
            ele2 {[dict]} -- second detection (in day2 schema)
            params {[dict]} -- A dictionary that has the following keys
                a. cam_overlap_adj_list: A adjacency list of which cameras
                have overlap with which other cameras. This key specifies the
                cameras which have overlapping coverages. If this
                dictionary has non-zero number of keys, then the tracker
                will only merge detections from the overlapping cameras.
                It will not merge between the cameras that do not overlap;
                it will always be kept separate

        Returns:
            [boolean] -- True if two detections are from overlapping cameras.
            False otherwise
        """
        cam_overlap_adj_list = params['cam_overlap_adj_list']

        retval = False
        cam1 = trackerutils.get_camera(ele1)
        cam2 = trackerutils.get_camera(ele2)
        cam_list = cam_overlap_adj_list.get(cam1, None)
        cam_list2 = cam_overlap_adj_list.get(cam2, None)
        if(cam_list is None) and (cam_list2 is None):
            return True
        # We are assuming the graph is bidirectional and edge is listed in
        # adj list of either of the ends
        if((cam_list is not None) and (not cam_list) and
           (cam2 in cam_list)):
            retval = True
        else:
            if((cam_list2 is not None) and (not cam_list2) and
               (cam1 in cam_list2)):
                retval = True
        return retval

    def concatenate_member_ids(self, json_list):
        """
        Given all the objects in json_list, create a list of all ids
        for as a list and return the list of ids

        Arguments:
            json_list {[type]} -- List of day2 schema based dictionaries
            for detections

        Returns:
            [list] -- List of ids
        """
        id_list = []
        for ele in json_list:
            id_list.append(ele["object"]["id"])
        return id_list

    def get_direction(self, ele1, ele2, dist_thresh=0):
        """
        Get the direction between detections ele1 and ele2 detections.
        This is usually used if the same object moves between two locations
        and we need to find the direction of movement

        Arguments:
            ele1 {[dict]} -- first detection (in day2 schema)
            ele2 {[dict]} -- second detection (in day2 schema)

        Keyword Arguments:
            dist_thresh {int} -- Mininum distance to compute direction.
            If the distance is less than this distance then the
            current direction (As tagged in the ele1) is returned
            (default: {0})

        Returns:
            [type] -- The direction in degrees [0,360)
        """
        first_pt = (ele1['object']['coordinate']['x'],
                    ele1['object']['coordinate']['y'])
        last_pt = (ele2['object']['coordinate']['x'],
                   ele2['object']['coordinate']['y'])

        # Compute direction only if dist beween two points is more than x
        dist_in_m = spatial.get_euc_dist(first_pt, last_pt)
        orientation = None
        if dist_in_m > dist_thresh:
            orientation_rad = spatial.get_radangle_flat_earth(
                first_pt, last_pt)
            orientation = math.degrees(orientation_rad)
        else:
            orientation = ele1['object']['direction']
        return orientation

    def update_direction(self, ele, direction):
        """[summary]
        Update the direction of the detection in ele by the given direction
        Arguments:
            ele {[dict]} -- detection in day2 schema
            direction {[float]} -- Direction in degrees [0,360)
        """
        if direction is not None:
            ele['object']['direction'] = direction
            ele['object']['orientation'] = direction

    def store_parked_cars(self, json_list):
        """
        Store the state of a parking spot

        Arguments:
            json_list {[list]} -- List of detections in day2 schema
        """
        for rec in json_list:
            if trackerutils.is_parked_rec(rec):
                # Use updateState in sparkStreaming
                parking_spot_id = rec['place']['parkingSpot']['id']
                # -- logging.debug("Storing Parked Car: {} : {}:{}:{}"
                # -- .format(parking_spot_id,
                # --         rec['object']['id'], get_camera(rec),
                # --         get_vehicle_string(rec)))

                if(self.state.parking_spot_state.get(parking_spot_id, None)
                   is None):
                    self.state.parking_spot_state[parking_spot_id] = rec
                else:
                    _ = self.state.parking_spot_state[parking_spot_id]
                    # -- logging.warning("WARNING: SPOT: DUP SPOT: PARKED: "
                    # -- "Already a car stored at index {}: Stored Car: "
                    # -- "{}:{}:{}:{}:{} , New car: {}:{}:{}:{}:{}".format(
                    # -- parking_spot_id, old_rec['@timestamp'],
                    # -- old_rec['object']['id'], get_camera(
                    # -- old_rec),
                    # -- get_vehicle_string(
                    # -- old_rec), old_rec['place']['id'],
                    # -- rec['@timestamp'], rec['object']['id'], get_camera(
                    # -- rec), get_vehicle_string(rec), rec['place']['id']
                    # -- ))

    def add_synthetic_attr(self, json_list):
        """
        If the vehicle detected does not have any attributes
        (e.g., license plate, color), then add dummy attributes

        Arguments:
            json_list {[list]} -- List of detections in day2 schema
        """
        for json_ele in json_list:
            curr_vehicle = trackerutils.get_vehicle_string(json_ele)
            # curr_obj_id = ""
            # -- logging.debug("\tChecking to add syn attribute: veh_str = {}"
            # -- " objid={}".format(curr_vehicle, curr_obj_id))
            if curr_vehicle == constants.UNK_VEH_KEY_STR_FORMAT:
                vehicle_json = constants.SYN_VEHICLE_STRUCT.copy()
                parked_str = "P" if trackerutils.is_spot_rec(json_ele) else "M"
                veh_id = ('UNK-' + parked_str + "-"
                          + str(self.state.curr_unknown_veh_id))
                # veh_id = get_random_lp()
                json_ele['object']['vehicle'] = vehicle_json
                json_ele['object']['vehicle']['license'] = veh_id
                # -- logging.debug("\tAdd syn attribute: veh_str = {} new_str={}".format(
                # --     curr_vehicle, get_vehicle_string(js)))
                self.state.curr_unknown_veh_id += 1

    def prune_carry_over_list(self, carry_over_list, timestamp):
        """
        Prune the carry over list. The cars that are not matched are carried over
        to the next timestep. However, if the car that was carried over is more
        than mcconfig.carry_over_time_in_sec seconds earlier, we prune them
        off the list

        Returns:
            [tuple] -- A tuple of (carry_over_list, removed_cars) where
                carry_over_list = The new carry over list
                removed_cars = The list of vehicles that were pruned
        """
        i = 0
        removed_cars = []
        while i < len(carry_over_list):
            ele = carry_over_list[i]
            # -- logging.debug("ts={}:{}".format(timestamp, type(timestamp)))
            # -- logging.debug("ele ts={}: {}".format(
            # --     ele["@timestamp"], type(ele["@timestamp"])))
            ele_ts = iso8601.parse_date(ele["@timestamp"])
            delta_time = (timestamp - ele_ts).total_seconds()
            if delta_time > self.config.carry_time_sec:
                removed_cars.append(carry_over_list[i])
                del carry_over_list[i]
            else:
                i += 1
        return carry_over_list, removed_cars

    def remove_empty_spots(self, timestamp, json_list):
        """
        If an empty spot is declared, then the car that was pulled has to be
        removed from the parking-spot-state-store.
        Arguments:
            timestamp {[datetime]} -- current timestamp
            json_list {[list]} -- List of detections in day2 schema

        Returns:
            [list] -- Day2 schema of the vehicles that were removed
        """
        added_virtual_records = []
        for rec in json_list:
            if trackerutils.is_empty_spot_rec(rec):
                # Use updateState in sparkStreaming
                parking_spot_id = rec['place']['parkingSpot']['id']
                # -- logging.debug("\t\tEmpty Spot: {} : {}".format(
                # --     parking_spot_id, rec['place']['id']))
                if(self.state.parking_spot_state.get(parking_spot_id, None)
                   is not None):
                    old_rec = self.state.parking_spot_state[parking_spot_id]
                    new_rec = copy.deepcopy(old_rec)
                    new_rec['place'] = copy.deepcopy(rec['place'])
                    new_rec['sensor'] = copy.deepcopy(rec['sensor'])
                    new_rec["@timestamp"] = trackerutils.get_timestamp_str(
                        timestamp)
                    added_virtual_records.append(new_rec)
                    # -- logging.debug("\t\tCar that was parked: {}:{}: Stored"
                    # -- " Car: {}:{}:{}:{}".format(
                    # -- parking_spot_id, rec['place']['id'],
                    # -- old_rec['object']['id'], get_camera(old_rec),
                    # -- get_vehicle_string(
                    # -- old_rec), old_rec['place']['id'],
                    # -- ))
                    del self.state.parking_spot_state[parking_spot_id]
                else:
                    # -- logging.warning("WARNING: SPOT: DUP EMPTY SPOT: "
                    # -- "EMPTY: The spot was already empty {}"
                    # -- .format(parking_spot_id))
                    pass

        return added_virtual_records

    # Functions visible to outside
    def process_batch(self, all_json_list):
        """"
        This is the main method that will be called for multicam tracking. The
        detections are passed in day2 schema in a list (all_json_list). This
        method returns nothing. The tracked objects are stored in the variable
        state.retval

        Arguments:
            all_json_list {[list]} -- List of detections in day2 schema
        """

        # Removing the retval from previous iteration
        # retval=state_dict.get("retval",[])
        retval = []

        if not all_json_list:
            return

        self.init_transforms(all_json_list)
        match_id = self.state.match_id

        # All the records are within one batch (say, within 0.5 seconds).
        # Choose one representative timestamp. Make sure its fast (no O(n), etc)
        timestamp = iso8601.parse_date(all_json_list[0]['@timestamp'])

        # Spot becomes occupied:
        #   1. You need to put the car into json_list so that we can match
        #      it to some car in prev_json_list
        #   2. Add the debug about parked car into some state
        #
        # Spot becomes free:
        #   1. Get the parked car debug from the state (transfer
        #      attributes from state)
        #   2. Do not match it at time t
        #   3. However, put it into the prev_json_list so that we can
        #      match the car at time t+1
        state_recs = self.get_vehicles_in_difft_states(all_json_list)
        # -- logging.debug("NEW TS: {}: {} : #={} M={} P={}".format(
        # -- match_id, timestamp, len(all_json_list),
        # -- len(state_recs['moving']), len(state_recs['parked'])))
        params = {
            "cam_overlap_adj_list":
                self.state.overlappig_camera_ids,
            "conflict_cameras_adj_list":
                self.state.conflict_cameras_adj_list,
            "dist_thresh": self.config.cl_dist_thresh_m
        }

        ind = 0
        for json_ele in state_recs['moving']:
            aisle_id = json_ele['place'].get('aisle', {}).get('id', None)
            if aisle_id is None:
                aisle_id = (json_ele['place']
                            .get('entrance', {})
                            .get('id', None))
                if aisle_id is None:
                    aisle_id = (json_ele['place']
                                .get('exit', {})
                                .get('id', None))
            # -- logging.debug("\t{}: {}: {}".format(
            # -- ind, js['@timestamp'], aisle_id))
            ind += 1

        state_recs = self.prune_nearby_points(
            timestamp, state_recs, params)
        self.store_parked_cars(state_recs['parked'])

        unidentified_cars = self.state.unidentified_cars
        # Now get all cars that were parked before and the spot is now
        # empty. Note this will come late because of smoothing. Hence,
        # the actual car might have actually passed by the time we get
        # this info. Somehow we have go back in time and change
        # transfer attributes
        _ = self.remove_empty_spots(
            timestamp, state_recs['emptySpots'])

        # For this version, do not match trajectory to parked car in the
        # tracking module
        # matched_pulled_car_list = (
        #   self.match_existing_trajs_with_pulled_car(timestamp,
        #   prev_parked_cars_now_moving, unidentified_cars, match_id))
        matched_pulled_car_list = []

        # -- logging.debug("\tPruned:#={}".format(
        # -- len(state_recs['moving'])))
        json_list = state_recs['moving']

        if constants.SNAP_POINTS_TO_GRAPH:
            self.match_moving_points_to_map(
                json_list, map_info=self.state.map_info)

        prev_json_list = self.state.prev_list
        prev_timestamp = self.state.prev_timestamp
        carry_over_list = self.state.carry_over_list

        # retval=[]
        if prev_json_list is not None:

            match_ret = self.match_points(
                prev_json_list, json_list, prev_timestamp, timestamp,
                params, match_id)

            # Do not maintain traj info in this version of the tracker
            # self.maintain_traj_info(prev_json_list, json_list,
            #   match_ret)

            carry_over_list = match_ret["carryOver"]
            # unassigned_prev = [prev_json_list[i]
            #                   for i in
            #                   match_ret["unassignedPrevListIndicies"]]
            unassigned_this = [json_list[i]
                               for i in
                               match_ret["unassignedListIndicies"]]

            tmp_match_stats = match_ret["stats"]

            # -- if(carry_over_list is not None and len(carry_over_list) > 0):
            # --     logging.debug("\tCARRY_OVER={}".format(
            # --    [str(i["@timestamp"]) + "@" +
            # --    reid.get_vehicle_string(i) +
            # --    ":" + str(i["object"]["id"]) for i in carry_over_list]))

            # -- if((unassigned_prev is not None) and
            # --    (len(unassigned_prev) > 0)):
            # --     logging.debug("\tUNASSIGNED PREV={}".format(
            # --        [reid.get_vehicle_string(
            # --         js) + " : " + str(js["object"]["id"]) + ":" +
            # --         str(js["@timestamp"]) for js in unassigned_prev]))
            # --     logging.debug("\tPREV={}".format(
            # --        [reid.get_vehicle_string(
            # --         js) + " : " + str(js["sensor"]["id"]) + " :" +
            # --        str(js["@timestamp"]) for js in prev_json_list]))
            # --     logging.debug("\tTHIS={}".format([
            # --         reid.get_vehicle_string(
            # --         js) + " : " + str(js["sensor"]["id"]) + ":" +
            # --        str(js["@timestamp"]) for js in json_list]))

            if(unassigned_this is not None) and unassigned_this:
                # -- logging.debug("\tAdding syn: UNASSIGNED THIS={}"
                # --    .format(
                # --     [str(i["@timestamp"]) + "@" +
                # --     reid.get_vehicle_string(i)
                # --     for i in unassigned_this]))
                # -- logging.debug("\tPREV={}".format([
                # --    reid.get_vehicle_string(
                # --    js) + " : " + str(js["sensor"]["id"]) + " :" +
                # --    str(js["@timestamp"]) for js in prev_json_list]))
                # -- logging.debug("\tTHIS={}".format([
                # --    reid.get_vehicle_string(
                # --    js) + " : " + str(js["sensor"]["id"]) + " :" +
                # --    str(js["@timestamp"]) for js in json_list]))
                # Something new appeared
                self.add_synthetic_attr(unassigned_this)

            # add_synthetic_attributes_if_necessary(state_recs['parked'])
            # add_synthetic_attributes_if_necessary(state_recs['pulled'])
            retval += (json_list + matched_pulled_car_list +
                       state_recs['emptySpots'] + state_recs['others'] +
                       state_recs['parked'])

            match_stats = self.state.match_stats
            match_id += 1
            match_stats += tmp_match_stats
            self.state.match_id = match_id
        else:
            # This is the first record set. If there are unknown vehicles,
            # then add them syn ids
            self.add_synthetic_attr(json_list)

        carry_over_list, _ = self.prune_carry_over_list(
            carry_over_list, timestamp)

        # Do not keep track of unidentified cars in the tracker
        # unidentified_cars = self.add_and_prune_unidentified_cars(
        #    timestamp, json_list, unidentified_cars)
        unidentified_cars = []
        self.state.unidentified_cars = unidentified_cars
        # -- logging.debug("\tMain: Unidentified cars: #={}"
        # -- .format(len(unidentified_cars)))

        possible_parked_cars = self.state.possible_parked_cars
        # Do not keep track of parked vs moving cars in the tracker
        # possible_parked_cars = self.add_and_prune_possible_parked_cars(
        #    timestamp, possible_parked_cars, removed_cars)

        possible_parked_cars = []
        # -- logging.debug("Possible Parked Cars before matching={}".format(
        # --     len(possible_parked_cars)))

        # Do not keep track of parked vs non parked cars in the tracker
        # matched_parked_cars, unmatched_parked_cars = (
        #   reid.match_parked_cars(prev_timestamp, possible_parked_cars +
        #   carry_over_list, timestamp, state_recs['parked'], match_id)
        matched_parked_cars, unmatched_parked_cars = ([], [])

        # Add the matched car from past + the matching parked car into
        # retval
        for rec in matched_parked_cars:
            retval += [rec[0], rec[1]]

        # If there are any parked cars left, send it out
        retval += unmatched_parked_cars

        if((len(matched_parked_cars) + len(unmatched_parked_cars)) !=
           len(state_recs['parked'])):
            logging.debug("ERROR: Total parked cars does not match"
                          " matched + unmatched parked cars: Total: %d : "
                          "Matched=%d Not matched=%d",
                          len(state_recs['parked']),
                          len(matched_parked_cars),
                          len(unmatched_parked_cars))

        # Prune the object ids that are mapped to same clusters
        self.prune_cluster_id_sets(timestamp)
        self.state.retval = retval
        logging.info("ProcessBatch: Retval=%d", len(self.state.retval))

        tmp_matched_moving_cars = [rec[0] for rec in matched_parked_cars]
        possible_parked_cars = [
            rec for rec in possible_parked_cars
            if rec not in tmp_matched_moving_cars]
        self.state.possible_parked_cars = possible_parked_cars
        # -- logging.debug("Possible Parked Cars after matching={}"
        # -- .format(len(possible_parked_cars)))
        carry_over_list = [
            rec for rec in carry_over_list
            if rec not in tmp_matched_moving_cars]
        self.state.carry_over_list = carry_over_list
        curr_moving_cars = [
            json_ele for json_ele in json_list
            if not trackerutils.is_parked_rec(json_ele)]
        prev_json_list = curr_moving_cars + carry_over_list
        self.state.prev_list = prev_json_list
        prev_timestamp = timestamp
        self.state.prev_timestamp = prev_timestamp

        # Flush the files, if logging is enabled
        self.mclogger.flush_files()

    def remove_all_additional_fields(self, json_list):
        """
        The tracker adds additional fields to the detection dictionaries that
        are passed. This will violate the day2 schema. Use this method to
        remove all additional fields that might be added by the tracker

        Arguments:
            json_list {[list]} -- List of detections in day2 schema
        """

        added_fields_obj_coord = ["origPoints"]
        for json_ele in json_list:
            for field in added_fields_obj_coord:
                if json_ele.get('object', {}).get("id_list", None) is not None:
                    del json_ele['object']['id_list']
                if(json_ele.get('object', {}).get('coordinate', {})
                   .get(field, None) is not None):
                    del json_ele['object']['coordinate'][field]

            if json_ele.get('traj', None) is not None:
                # logging.debug("traj present.. removing")
                del json_ele['traj']
                # logging.debug("js={}".format(js))
