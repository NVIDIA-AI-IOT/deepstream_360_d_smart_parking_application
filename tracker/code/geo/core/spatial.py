"""
Spatial helper files
"""

__version__ = '0.2'

import math
import numpy as np

import pysal.cg.sphere as sphere


def geointerpolate(point0, point1, proportion):
    """Interpolate on great sphere (world coords)

    Arguments:
        point0 {list} -- (lng,lat) of first point
        point1 {list} -- (lng,lat) of first point
        proportion {float} -- the interpolation distance

    Returns:
        list -- the list of interpolated points (lng,lat)
    """
    return sphere.geointerpolate(point0, point1, proportion)


def geo_distance_in_km(pt1, pt2):
    """
    Get the distance in km between two (lng,lat) poinmts

    Arguments:
        pt1 {list} -- (lng,lat) of first point
        pt2 {list} -- (lng,lat) of second point

    Returns:
        float -- Ditance between pt1 and pt2
    """
    return sphere.harcdist(pt1, pt2)


def get_nearest_point(kdtree, the_pt, dist_thresh_in_km=0.005):
    """
    Get the nearest point to "the_pt" using the the kd=tree index

    Arguments:
        kd {[KDTree]} -- The KD-tree of all the points
        the_pt {list} -- [x,y] of the point

    Keyword Arguments:
        dist_thresh_in_km {float} -- The maximum distance (in km) within
            which the nearest points have to be searched (default: {0.005})

    Returns:
        list -- A tuple of the nearest point in the tuple
            (distance, point index)
    """
    dist_in_km, ind = kdtree.query(the_pt, k=1)
    if dist_in_km is not None and dist_in_km <= dist_thresh_in_km:
        return dist_in_km, ind
    return None, None


def add_graph_attr_to_entry_exit(entry_points, kd_points,
                                 points_arr, rev_point_dict):
    """
    Enhance the graph attributes for entry and exit points

    Arguments:
        entry_points {list} -- List of entry points
        kd_points {KDTree} -- KDTree of points
        points_arr {list} -- list of points
        rev_point_dict {dictionary} -- A dictionary mapping points to ids
    """
    for ept in entry_points:
        _, ind = get_nearest_point(
            kd_points, ept["approx_coordinate"], dist_thresh_in_km=0.005)
        if ind is not None:
            ept['node_id'] = rev_point_dict[points_arr[ind]]


def get_lng_lat_coord(origin_lnglat, xy_pt):
    """
    Get the (lng, lat) from a given eucledian point (x,y). The origin point is
    given by origin_lnglat in (longitude, latitude) format. We assume (x,y)
    is "x" kilometers along longitude from the origin_lnglat, and "y"
    kilometers along the latitude.
    NOTE: (x,y) is in km from origin (and NOT in meters)

    Arguments:
        origin_lnglat {list} -- The (longitude,latitude) of the origin point
        xy_pt {tuple} -- The (x,y) point (see above for details)

    Returns:
        list -- The (longitude, latitude) of the (x,y) point
    """
    ret_pt = list((0, 0))
    (var_dx, var_dy) = xy_pt
    ret_pt[1] = origin_lnglat[1] - (var_dy * 360.0 / 40000.0)
    ret_pt[0] = origin_lnglat[0] - \
        (var_dx * 360.0 /
         (40000.0 * math.cos((origin_lnglat[1] + ret_pt[1]) * math.pi /
                             360.0)))
    ret_pt = tuple(ret_pt)
    return ret_pt


def get_flat_earth_coord(origin, the_pt):
    """
    Get the flat earth coordinates (x,y) from a given (lng,lat) point "pt".
    The (x,y) is the offset in lng and lat dimensions (in meters or km)
    from a given origin point (olng, olat)

    Arguments:
        origin {list} -- (lng,lat) of the origin point
        pt {list} -- (lnt,lat) of the point

    Returns:
        [type] -- [description]
    """
    vardx = ((origin[0] - the_pt[0]) * 40000.0 *
             math.cos((origin[1] + the_pt[1]) * math.pi / 360) / 360)
    vardy = (origin[1] - the_pt[1]) * 40000.0 / 360
    return vardx, vardy


def get_euc_dist(pt1, pt2):
    """
    Get eucledian distance between two points pt1 and pt2
    Note that we assume we pass flat earth coords (x,y)
    and (lng,lat), since eucledian distance of (lng,lat)
    does not yield meaningful distances

    Arguments:
        pt1 {[type]} -- [description]
        pt2 {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    return math.hypot(pt2[0] - pt1[0], pt2[1] - pt1[1])


def get_radangle_flat_earth_old(pt1, pt2):
    """Get the angle for two given points (in flat earth coords)

    Arguments:
        pt1 {list} -- (x,y) for the first point
        pt2 {list} -- (x,y) for the first point

    Returns:
        float -- Angle (in radians) betweent pt1 and pt2
    """
    ydiff = pt1[1] - pt2[1]
    xdiff = pt1[0] - pt2[0]
    if abs(xdiff) < 1E-6:
        return math.pi / 2.0

    return math.atan(ydiff / float(xdiff))


def angle_trunc(the_angle):
    """
    Truncate the angle between [0, 360)

    Arguments:
        the_angle {float} -- angle

    Returns:
        float -- Angle between [0,360)]
    """
    while the_angle < 0.0:
        the_angle += math.pi * 2
    return the_angle


def get_radangle_flat_earth(the_pt1, the_pt2):
    """Get the angle for two given points (in flat earth coords)

    Arguments:
        pt1 {list} -- (x,y) for the first point
        pt2 {list} -- (x,y) for the first point

    Returns:
        float -- Angle (in radians) betweent pt1 and pt2
    """
    delta_y = the_pt2[1] - the_pt1[1]
    delta_x = the_pt2[0] - the_pt1[0]
    return angle_trunc(math.atan2(delta_y, delta_x))


def get_all_rects(rect, the_pt):
    """
    Get all rectangles for the point the_pt

    Arguments:
        rect {KDTree rect} -- Input rectangle kdtree
        the_pt {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    res = [r.leaf_obj() for r in rect.query_point(the_pt) if r.is_leaf()]
    return res


def get_angle_between_pts_on_sphere(the_pt1, the_pt2):
    """
    Get the angle between two points on a sphere

    Arguments:
        the_pt1 {list} -- (lng,lat) of first point
        the_pt2 {list} -- (lng,lat) of second point

    Returns:
        float -- angle in radians between first and second point
    """
    return sphere.radangle(the_pt1, the_pt2)


def get_origin(pt_dict):
    """
    Get the origin point of all points (mean lng and lat)

    Arguments:
        pt_dict {[list]} -- list of all points

    Returns:
        list -- the origin point
    """
    # Compute origin
    lngs = [v[0] for v in pt_dict.values()]
    lats = [v[1] for v in pt_dict.values()]
    origin = (np.mean(lngs), np.mean(lats))
    #origin_angle_rad = get_angle_between_pts_on_sphere((0,0), origin)
    return origin


def add_camera_attr_with_entry_exit(cameras_dict, cam_rtree,
                                    entry_point_attributes,
                                    exit_point_attributes):
    """Based on entry and exit points, we assign entry and exit camearas

    Arguments:
        cameras_dict {dict} -- Dict of cameras
        cam_rtree {RTree} -- R-tree of camera points
        entry_point_attributes {list} -- List of entry points
        exit_point_attributes {list} -- List of exit points
    """
    for ept in entry_point_attributes.values():
        the_pt = ept['approx_coordinate']
        cams = get_all_rects(cam_rtree, the_pt)
        cameras_detected = [cameras_dict[i] for i in cams]
        for cam in cameras_detected:
            cam['isEntryCamera'] = 1

    for ept in exit_point_attributes.values():
        the_pt = ept['approx_coordinate']
        cams = get_all_rects(cam_rtree, the_pt)
        cameras_detected = [cameras_dict[i] for i in cams]
        for cam in cameras_detected:
            cam['isExitCamera'] = 1
