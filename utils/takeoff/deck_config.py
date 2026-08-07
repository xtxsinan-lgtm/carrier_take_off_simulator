"""Shared ski-jump deck configuration helpers."""
from utils.takeoff.ski_jump_geometry import compute_ski_jump_arc


def assign_ski_jump_globals(globals_dict, angle_deg, lip_height_m=None):
    """Write ski-jump arc derived values into a module globals() mapping."""
    arc = compute_ski_jump_arc(angle_deg, lip_height_m=lip_height_m)
    globals_dict['SKI_JUMP_ARC'] = arc
    globals_dict['SKI_JUMP_ANGLE_DEG'] = arc.angle_deg
    globals_dict['SKI_JUMP_ANGLE_RAD'] = arc.angle_rad
    globals_dict['SKI_JUMP_RADIUS_M'] = arc.radius_m
    globals_dict['SKI_JUMP_ARC_LENGTH_M'] = arc.arc_length_m
    globals_dict['SKI_JUMP_HORIZONTAL_M'] = arc.horizontal_m
    globals_dict['SKI_JUMP_LIP_HEIGHT_M'] = arc.lip_height_m
    globals_dict['SKI_JUMP_COS'] = arc.cos_exit
    globals_dict['SKI_JUMP_SIN'] = arc.sin_exit
    globals_dict['SKI_JUMP_LENGTH_M'] = arc.arc_length_m


def total_takeoff_distance_m(flat_length_m, ski_jump_horizontal_m):
    return flat_length_m + ski_jump_horizontal_m
