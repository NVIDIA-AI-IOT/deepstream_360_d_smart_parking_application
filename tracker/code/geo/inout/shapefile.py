"""
This module is handles all shapefile operatoons
"""

__version__ = '0.2'

import shapefile

SORT_COORDS = False


def get_polygons_from_shape_file(sh_file):
    """Get all polygons from a given shape file

    Arguments:
        sh_file {[string]} -- The shapefile

    Returns:
        [list] -- list of polygons
    """
    shpfile = shapefile.Reader(sh_file)
    feature_list = []
    field_names = []
    index = 0
    if shpfile.fields:
        for fld in shpfile.fields[1:]:
            if fld:
                fname = fld[0]
            else:
                fname = "field_{}".format(index)
            field_names.append(fname)
            index += 1
    else:
        field_names = []

    index = 0
    for shape_rec in shpfile.shapeRecords():
        if shape_rec.shape.shapeType != shapefile.POLYGON:
            print("ERROR: We support only polygon shapes currently. The input "
                  "indicates some other shape(shapeType={}). Skipping this"
                  "shape.".format(shape_rec.shape.shapeType))
            continue

        if len(shape_rec.shape.points) != 5:
            print("Currently we support rectangles (polygons with 5 points "
                  "incl. end point repeated). Num points found: {}. Skipping "
                  "polygon. Features of polygon: {}"
                  .format(len(shape_rec.shape.points), shape_rec.record))
            continue

        pt_list = []
        # End point is repeated in the end. Omit it
        for point in shape_rec.shape.points[:-1]:
            pt_list.append(point)

        featuredict = {"points": pt_list}
        featuredict.update({field_names[i]: shape_rec.record[i]
                            for i in range(len(field_names))})
        feature_list.append(featuredict)
        index += 1

    return feature_list


def get_polylines_from_shape_file(sh_file):
    """
    Get a list of polygon lines (polylines)
    from shapefile

    Arguments:
        sh_file {[string]} -- the shapefile name

    Returns:
        [list] -- list of polylines
    """
    shpfile = shapefile.Reader(sh_file)
    feature_list = []
    field_names = []
    index = 0
    if shpfile.fields:
        for fld in shpfile.fields[1:]:
            if fld:
                fname = fld[0]
            else:
                fname = "field_{}".format(index)
            field_names.append(fname)
            index += 1
    else:
        field_names = []

    index = 0
    for shape_rec in shpfile.shapeRecords():
        if shape_rec.shape.shapeType != shapefile.POLYLINE:
            print("ERROR: The function reads only polylines. The input indicates"
                  " some other shape (shapeType={}). Skipping this shape."
                  .format(shape_rec.shape.shapeType))
            continue

        pt_list = []
        # End point is repeated in the end. Omit it
        for point in shape_rec.shape.points:
            pt_list.append(point)

        fielddict = {"points": pt_list}
        fielddict.update({field_names[i]: shape_rec.record[i]
                          for i in range(len(field_names))})
        feature_list.append(fielddict)
        index += 1

    return feature_list
