"""
Helper module for road-network related functions
"""

__version__ = '0.2'

import logging
import numpy as np
import networkx as nx
from pysal.cg import RTree, Rect
from sklearn.neighbors import KDTree
import pandas as pd
from euclidean import euchelper


class Network:
    """Class for the Network graph
    """

    def __init__(self, lines_arr, max_point_dist=0.1):
        self.pt_dict = {}
        self.adj_dict = {}
        self.rtree = RTree()

        # KD Tree related
        self.kd_tree = None
        self.points_kd = None
        self.kd_ptid_to_nodeid_map = {}
        self.kd_nodeid_to_ptid_map = {}
        self.kd_pt_data_list = []

        self.network = None
        self.refine_graph(lines_arr, max_point_dist)
        self.build_all_elements()

    def check_and_add_pt(self, point, min_dist, next_pt_id):
        """Check if a point is present. A point will be added if
        there are no other points within the "min_dist" neighborhood

        Arguments:
            point {[list]} -- [x,y] of the point
            min_dist {[float]} -- The minimum neighborhood distance
            next_pt_id {[int]} -- The starting id of the point that should
                be assigned for the next point

        Returns:
            [int] -- The next_id to be used for downstream calls
        """
        point_id = None
        res = [r.leaf_obj()
               for r in self.rtree.query_point(point) if r.is_leaf()]
        if(res is not None) and res:
            #logging.debug("\tREPEAT: point={}, res={}".format(point,res))
            point_id = res[0]
        else:
            pt0 = ((point[0] - float(min_dist / 2.0)),
                   (point[1] - float(min_dist / 2.0)))
            pt1 = ((point[0] + float(min_dist / 2.0)),
                   (point[1] + float(min_dist / 2.0)))
            self.rtree.insert(next_pt_id, Rect(pt0[0], pt0[1], pt1[0],
                                               pt1[1]))
            point_id = next_pt_id
        return point_id

    def refine_graph(self, lines_arr, max_point_dist):
        """
        Refine the graph by removing close points

        Arguments:
            lines_arr {[list]} -- List of lines
            max_point_dist {[float]} -- The max distance between two points
        """
        # Put all lines in an r-tree
        pt_id = 0

        add_reverse_edge = False
        #index = 0

        for line_string in lines_arr:

            prev_pt_id = None
            for point in line_string:
                add_pt_id = self.check_and_add_pt(point, max_point_dist, pt_id)
                if add_pt_id == pt_id:
                    # Point was added
                    self.pt_dict[add_pt_id] = point
                    pt_id += 1
                else:
                    # Point was already found
                    pass

                if prev_pt_id is not None:
                    # Add edge from src->dest
                    adj_list = self.adj_dict.get(prev_pt_id, None)
                    if adj_list is None:
                        adj_list = []
                    adj_list.append(add_pt_id)
                    self.adj_dict[prev_pt_id] = adj_list

                    # Add reverse edge (dst->src)
                    if add_reverse_edge:
                        adj_list = self.adj_dict.get(add_pt_id, None)
                        if adj_list is None:
                            adj_list = []
                        adj_list.append(prev_pt_id)
                        self.adj_dict[add_pt_id] = adj_list

                prev_pt_id = add_pt_id
        # logging.debug("pt_dict={}".format(self.pt_dict))

    def build_all_elements(self):
        """Build the network and create an indexing structure (kdtree)
        """
        self.build_network()
        self.create_point_kd()

    def create_point_kd(self):
        """Create a kdtree of points
        """
        index = 0
        node_list = self.network.nodes(data=True)
        for node, data in node_list:
            self.kd_nodeid_to_ptid_map[node] = index
            self.kd_ptid_to_nodeid_map[index] = node
            self.kd_pt_data_list.append([data["x"], data["y"]])
            index += 1

        if self.kd_pt_data_list:
            self.kd_pt_data_list = np.array(self.kd_pt_data_list)
            self.kd_tree = KDTree(self.kd_pt_data_list)

    def get_nearest_point_id(self, thept):
        """Get the first nearest point on the graph for a given "pt"

        Arguments:
            thept {[list]} -- [x,y] point

        Returns:
            [list] -- Nearest point
        """
        pt_id = None
        if self.kd_tree is not None:
            dist_arr, pt_ind_arr = self.kd_tree.query([thept], k=1)
            dist = dist_arr[0][0]
            pt_ind = pt_ind_arr[0][0]
            if self.kd_ptid_to_nodeid_map.get(pt_ind, None) is not None:
                pt_id = self.kd_ptid_to_nodeid_map[pt_ind]
            else:
                logging.error("ERROR: Nearest point for %s (ind=%d, pt=%s, "
                              "dist=%f) is not a part of kdtree",
                              str(thept), pt_ind,
                              str(self.kd_pt_data_list[pt_ind]), dist)
        return pt_id

    def build_network(self):
        """Build the road-network
        """
        self.network = nx.Graph()
        for pt_id in self.pt_dict:
            self.network.add_node(pt_id, x=self.pt_dict[pt_id][0],
                                  y=self.pt_dict[pt_id][1],
                                  pos=(self.pt_dict[pt_id][0],
                                       self.pt_dict[pt_id][1]))

        for src in self.adj_dict:
            for dst in self.adj_dict[src]:
                src_pt = np.array(self.pt_dict[src])
                dst_pt = np.array(self.pt_dict[dst])
                edge_len = np.linalg.norm(src_pt-dst_pt)
                self.network.add_edge(src, dst, weight=edge_len)

    def get_shortest_path_bw_id(self, start_point_id, dst_point_id):
        """Get the shortest path between given source and dest

        Arguments:
            start_point_id {[list]} -- [x,y] of the source point
            dst_point_id {[type]} -- [x,y] of the destination point

        Returns:
            [list] -- list of points [x,y]
        """
        retval = []
        try:
            retval = nx.shortest_path(
                self.network, source=start_point_id, target=dst_point_id,
                weight='weight')
        except nx.NetworkXNoPath:
            # No path found between two points
            retval = None
        return retval

    def get_xy(self, node_id):
        """
        Get the (x,y) position of a given node with id = "node_id"

        Arguments:
            node_id {[int]} -- The node id

        Returns:
            [list] -- The [x,y] of the node
        """
        if node_id in self.network:
            return (self.network.node[node_id]['x'],
                    self.network.node[node_id]['y'])
        else:
            return None

    def get_interpolated_path(self, st_pt, end_pt, ts_arr,
                              interpolate_time_sec=0.5, id_str=None):
        """
        Interpolate a path between st_pt and end_pt on the graph

        Arguments:
            st_pt {int} -- The id of the starting point
            end_pt {int} -- The id of the end point
            ts_arr {list} -- [list of timestamps for each visit]

        Keyword Arguments:
            interpolate_time_sec {float} -- The interpolation time
                (default: {0.5})
            id_str {string} -- The string id provided as a suffix to file
                (default: {None})
        """
        retval = []
        path = self.get_shortest_path_bw_id(st_pt, end_pt)
        if path is None:
            retval = None

        elif path:
            last_ts = ts_arr[len(ts_arr) - 1]
            start_ts = ts_arr[0]
            total_time_sec = (last_ts - start_ts) / np.timedelta64(1, 's')
            path_lth = 0
            path_pts = []
            prev_pt = None
            # Compute path length
            for node in path:
                thept = self.get_xy(node)
                if thept is not None:
                    thept = np.array(thept)
                    path_pts.append(thept)
                    if prev_pt is not None:
                        dist = np.linalg.norm(thept-prev_pt)
                        path_lth += dist
                    prev_pt = thept

            # Chop the distance into points based on speed and time
            time_diff = (ts_arr[len(ts_arr) - 1] -
                         ts_arr[0]) / np.timedelta64(1, 's')
            dist_km_per_hop = (path_lth *
                               interpolate_time_sec / float(total_time_sec))

            path_list = []
            prev_node = None
            prev_node_pt = None
            remaining_dist_on_this_hop = 0.0
            curr_ts = start_ts
            for node in path:
                thept = np.array(self.get_xy(node))
                if prev_node_pt is not None:
                    # Now interpolate with the distance
                    edge_len_km = np.linalg.norm(thept - prev_node_pt)

                    traversed_dist_on_this_hop = abs(
                        remaining_dist_on_this_hop)

                    if(remaining_dist_on_this_hop < 0 and
                       abs(remaining_dist_on_this_hop) < edge_len_km):

                        proportion = (
                            traversed_dist_on_this_hop / float(edge_len_km))
                        new_pt = euchelper.interpolate_line(
                            prev_node_pt, thept, proportion)
                        curr_lth = abs(remaining_dist_on_this_hop)
                        time_delta_this_hop_sec = (curr_lth *
                                                   time_diff / float(path_lth))
                        curr_ts = (curr_ts +
                                   pd.Timedelta(time_delta_this_hop_sec, unit='s'))
                        path_list.append({"ts": curr_ts, "edgept1": prev_node,
                                          "edgept2": node,
                                          "edgeX0": prev_node_pt[0],
                                          "edgeY0": prev_node_pt[1],
                                          "edgeX1": thept[0], "edgeY1": thept[1],
                                          "edgeLth": edge_len_km,
                                          "x": new_pt[0], "y": new_pt[1],
                                          "proportion": proportion,
                                          "currLth": curr_lth,
                                          "timeDelta": time_delta_this_hop_sec,
                                          "distOnHop": traversed_dist_on_this_hop,
                                          "remLth": remaining_dist_on_this_hop}
                                         )
                        retval.append(
                            [curr_ts, new_pt[0], new_pt[1], curr_lth])

                    remaining_dist_on_this_hop = edge_len_km + remaining_dist_on_this_hop

                    if remaining_dist_on_this_hop <= 0:
                        # Add entire edge
                        new_pt = thept
                        curr_lth = edge_len_km
                        remaining_dist_on_this_hop -= curr_lth

                        time_delta_this_hop_sec = curr_lth * \
                            time_diff / float(path_lth)
                        curr_ts = curr_ts + \
                            pd.Timedelta(time_delta_this_hop_sec, unit='s')
                        retval.append(
                            [curr_ts, new_pt[0], new_pt[1], curr_lth])
                        path_list.append({"ts": curr_ts,
                                          "edgeX0": prev_node_pt[0],
                                          "edgeY0": prev_node_pt[1],
                                          "edgeX1": thept[0],
                                          "edgeY1": thept[1],
                                          "x": new_pt[0],
                                          "y": new_pt[1],
                                          "edgeLth": edge_len_km,
                                          "proportion": 1.0,
                                          "currLth": curr_lth,
                                          "timeDelta": time_delta_this_hop_sec,
                                          "distOnHop": curr_lth,
                                          "remLth": remaining_dist_on_this_hop}
                                         )
                    else:
                        while remaining_dist_on_this_hop >= 0.0:
                            # Now keep interpolating
                            curr_lth = dist_km_per_hop  # about 0.7
                            traversed_dist_on_this_hop += curr_lth
                            remaining_dist_on_this_hop = edge_len_km - traversed_dist_on_this_hop

                            if traversed_dist_on_this_hop > edge_len_km:
                                curr_lth = (edge_len_km -
                                            (traversed_dist_on_this_hop - curr_lth))
                                traversed_dist_on_this_hop = edge_len_km

                            proportion = (traversed_dist_on_this_hop /
                                          float(edge_len_km))
                            new_pt = euchelper.interpolate_line(
                                prev_node_pt, thept, proportion)
                            time_delta_this_hop_sec = (curr_lth *
                                                       time_diff / float(path_lth))
                            curr_ts = (curr_ts +
                                       pd.Timedelta(time_delta_this_hop_sec, unit='s'))
                            path_list.append({"ts": curr_ts,
                                              "edgept1": prev_node,
                                              "edgept2": node,
                                              "edgeX0": prev_node_pt[0],
                                              "edgeY0": prev_node_pt[1],
                                              "edgeX1": thept[0],
                                              "edgeY1": thept[1],
                                              "edgeLth": edge_len_km,
                                              "x": new_pt[0],
                                              "y": new_pt[1],
                                              "proportion": proportion,
                                              "currLth": curr_lth,
                                              "timeDelta": time_delta_this_hop_sec,
                                              "distOnHop": traversed_dist_on_this_hop,
                                              "remLth": remaining_dist_on_this_hop})
                            retval.append(
                                [curr_ts, new_pt[0], new_pt[1], curr_lth])

                else:
                    # First point
                    retval.append([curr_ts, thept[0], thept[1], 0])
                    path_list.append({"ts": curr_ts, "edgept1": prev_node,
                                      "edgept2": node, "edgeX0": None,
                                      "edgeY0": None,
                                      "edgeX1": thept[0],
                                      "edgeY1": thept[1],
                                      "x": thept[0],
                                      "y": thept[1],
                                      "edgeLth": None,
                                      "proportion": None,
                                      "currLth": None,
                                      "timeDelta": None,
                                      "distOnHop": None,
                                      "remLth": remaining_dist_on_this_hop})
                prev_node = node
                prev_node_pt = thept
                pd.DataFrame(path_list).to_csv(
                    "pathBreaks_{}.csv".format(id_str), index=False)

        if(retval is not None) and (len(retval) > 2):
            path_list = []
            index = 0
            curr_ts = start_ts
            lth_vec = [ele[3] for ele in retval]
            total_lth = float(np.sum(lth_vec))
            curr_ts = start_ts
            for ent in retval:
                ent[0] = curr_ts
                time_inc = ent[3] * total_time_sec / float(total_lth)
                curr_ts = curr_ts + pd.Timedelta(time_inc, unit='s')
                index += 1
                path_list.append(
                    {"ts": ent[0], "edgeX0": ent[1], "edgeY0": ent[2]})

            pd.DataFrame(path_list).to_csv(
                "pathBreaks_final_{}.csv".format(id_str), index=False)

        return retval

    def draw_network(self):
        """
        Draw the network using matplotlib
        """

        if self.network is not None:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(20, 10))
            pos = nx.get_node_attributes(self.network, 'pos')
            nx.draw(self.network, pos, with_labels=True)

            plt.show()
