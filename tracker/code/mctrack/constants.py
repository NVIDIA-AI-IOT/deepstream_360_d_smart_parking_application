"""
Constants etc
"""

__version__ = '0.2'

# Global configuration variables
# ================================
# Constants for options
# ----------------------------------
SNAP_POINTS_TO_GRAPH = False
TAKE_ONE_FRAME_PER_PERIOD = True
ASSUME_OBJS_HAVE_SAME_ID_INTRA_FRAME_PERIOD = True
MERGE_CLOSE_BBS_FROM_SAME_CAM = True
APPROX_TIME_PERIOD_TO_PRINT_INFO_IN_SEC = 10.0


# Sensitive thresholds (Be careful while tuning)
# ---------------------------------

# Clustering thresholds
DEF_CLUS_DIST_THRESH_M = 25.0

# Matching thresholds
DEF_MATCH_MAX_DIST_IN_M = 20.0
MATCH_MAX_DIST_FOR_PULLED_CAR = 10.0

# How long to hold points for matching
DEF_CARRY_PRUNE_TIME_SEC = 2.5


# Not so sensitive features to tune
# ---------------------------------
CLUSTERED_OBJ_ID_PRUNETIME_SEC = 20

MIN_THRESHOLD_DIST_IN_M_WITHIN_RESAMPLE_TIME = 1
INTRA_FRAME_PERIOD_CLUST_DIST_IN_M = 1.5
INTRA_FRAME_CLUSTER_LARGE_SCALE_FACTOR = 10
CLUSTER_DIFFT_CAMERAS_LARGE_SCALE_FACTOR = 10.0

CARRY_OVER_LIST_PRUNE_TIME_IN_SEC = 2.5
# HOLD_FOR_PARKED_CAR_PRUNE_TIME_IN_SEC = 30.0
# HOLD_FOR_PULLED_CAR_PRUNE_TIME_IN_SEC = 30.0
HOLD_FOR_PARKED_CAR_PRUNE_TIME_IN_SEC = 0.0
HOLD_FOR_PULLED_CAR_PRUNE_TIME_IN_SEC = 0.0

# Distance normalization thresholds
DEFAULT_DIST_NORM_XRANGE = 1
DEFAULT_DIST_NORM_YRANGE = 1
DEFAULT_DIST_NORM_MINX = 0
DEFAULT_DIST_NORM_MINY = 0

# Snapping to map thresholds
MAX_DIST_SNAP_MAP = 20.0

# Camera and frame rate related variables
# ---------------------------------
# Frame periodicity
RESAMPLE_TIME_IN_SEC = 0.5

# Other constants
# -----------------------------------
VEH_KEY_STR_FORMAT = "{}"
UNK_VEH_KEY_STR_FORMAT = VEH_KEY_STR_FORMAT.format('')
SYN_VEHICLE_STRUCT = {"make": "UNKNOWN",
                      "model": "UNKNOWN",
                      "color": "UNKNOWN",
                      "confidence": 0.0,
                      "license": "UNKNOWN",
                      "licenseState": "UNKNOWN",
                      "type": "UNKNOWN"}
