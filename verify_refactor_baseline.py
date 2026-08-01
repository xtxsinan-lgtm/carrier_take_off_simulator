"""Capture numeric snapshots for refactor noop verification."""
import contextlib
import io
import json
import short_take_off as flat
import short_ski_jump_take_off as ski_stovl
import ski_jump_take_off as ski_conv


def snap_flat():
    return {
        "rho": flat.RHO,
        "thrust_factor": flat.THURST_TEMP_FACTOR if hasattr(flat, 'THURST_TEMP_FACTOR') else flat.THRUST_TEMP_FACTOR,
        "oswald": flat.calc_oswald_e(flat.ASPECT_RATIO, flat.SWEEP_LE_DEG),
        "cl_alpha": flat.calc_cl_alpha(flat.ASPECT_RATIO, flat.OSWALD_E, flat.SWEEP_LE_DEG),
        "phi": flat.calc_ground_effect_phi(flat.WING_HEIGHT_M, flat.WINGSPAN_M),
        "exhaust_30": flat.calc_exhaust_safe_distance_m(30.0, flat.V_WIND_MPS),
        "exhaust_theta": flat.calc_exhaust_theta_deg_for_safe_distance_m(50.0, flat.V_WIND_MPS),
        "min_nozzle": flat.calc_min_nozzle_deg_for_plume(100.0, flat.MIN_SAFE_DISTANCE_M, flat.V_WIND_MPS),
        "strategy_c": flat.simulate_strategy_c(flat.MIN_SAFE_DISTANCE_M),
    }


def snap_ski_stovl():
    with contextlib.redirect_stdout(io.StringIO()):
        r = ski_stovl.search_strategy_c(ski_stovl.MIN_SAFE_DISTANCE_M)
    return {
        "rho": ski_stovl.RHO,
        "arc_horizontal": ski_stovl.SKI_JUMP_HORIZONTAL_M,
        "exhaust_30": ski_stovl.calc_exhaust_safe_distance_m(30.0, ski_stovl.V_WIND_MPS),
        "total_dist": ski_stovl.total_takeoff_distance_m(100.0),
        "simulate_ab": ski_stovl.simulate(80.0, 20.0, 45.0, "A", 20.0),
        "strategy_c": r,
    }


def snap_ski_conv():
    with contextlib.redirect_stdout(io.StringIO()):
        best = ski_conv.search_flat_length()
    return {
        "rho": ski_conv.RHO,
        "best_flat": best,
        "simulate_100_15": ski_conv.simulate(100.0, 15.0)[:5],
    }


def main():
    data = {
        "flat": snap_flat(),
        "ski_stovl": snap_ski_stovl(),
        "ski_conv": snap_ski_conv(),
    }
    print(json.dumps(data, default=str, indent=2))


if __name__ == "__main__":
    main()
