"""AV-8B 排气与 Pegasus 参数单元测试。"""
import pytest

from utils.database_csv import load_aircraft_csv
from utils.exhaust_plume import (
    PEGASUS_AIRFLOW_LB_S,
    calc_exhaust_d0_from_engine_diameter,
    calc_exhaust_u0_from_thrust_mdot,
    estimate_rcs_rollpost_thrust_n,
    lb_s_to_kg_s,
)
from utils.paths import AIRCRAFT_CSV


def test_pegasus_mdot_from_public_airflow():
    assert lb_s_to_kg_s(PEGASUS_AIRFLOW_LB_S) == pytest.approx(195.95, rel=0.01)


def test_av8b_exhaust_u0_from_thrust_mdot():
    thrust_n = 105_000.0
    mdot = lb_s_to_kg_s(432.0)
    u0 = calc_exhaust_u0_from_thrust_mdot(thrust_n, mdot)
    assert u0 == pytest.approx(535.8, rel=0.02)


def test_av8b_d0_from_engine_diameter():
    d0 = calc_exhaust_d0_from_engine_diameter(1.219)
    assert d0 == pytest.approx(1.219, rel=0.01)


def test_rcs_rollpost_thrust_estimate():
    bleed_kg_s = lb_s_to_kg_s(7.0)
    thrust = estimate_rcs_rollpost_thrust_n(bleed_kg_s, 340.0)
    assert thrust == pytest.approx(1080.0, rel=0.05)


def test_av8b_loaded_from_csv():
    ac = load_aircraft_csv(AIRCRAFT_CSV)['AV-8B']
    assert ac.is_vtol
    assert ac.has_lift_fan is False
    assert ac.t_main_stovl_sl_n == pytest.approx(105_000)
    assert ac.t_liftfan_sl_n == pytest.approx(0)
    assert ac.wingspan_m == pytest.approx(9.25)
    assert ac.wing_area_m2 == pytest.approx(21.37)
    assert ac.sweep_le_deg == pytest.approx(37)
    plume = ac.exhaust_plume_params()
    assert plume.mdot_kg_s == pytest.approx(195.95, rel=0.01)
    assert plume.u0_mps == pytest.approx(535.8, rel=0.02)
    assert plume.d0_m == pytest.approx(1.219, rel=0.01)
