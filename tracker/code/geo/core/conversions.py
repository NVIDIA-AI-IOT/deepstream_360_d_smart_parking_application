"""Convert geo shapes
"""

__version__ = '0.2'


def poly_lines_to_lines(polyline_list):
    """Convert a set of polylines to a simple lines (start and end points)

    Arguments:
        polyline_list {list} -- Set of polylines

    Returns:
        list -- Set of lines
    """
    line_list = []

    for polyline in polyline_list:
        prev_pt = None
        for the_pt in polyline:
            if prev_pt is not None:
                line_list.append([prev_pt, the_pt])
            prev_pt = the_pt
    return line_list
