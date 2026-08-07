"""涡桨 / 倾转旋翼推力换算单元测试。"""
from __future__ import annotations

import math

import pytest

from utils.takeoff.propeller_thrust import (
    calc_effective_disk_area_m2,
    calc_ideal_static_thrust_n,
    calc_ideal_thrust_with_axial_speed_n,
    calc_prop_disk_area_m2,
    calc_propeller_thrust_n,
)


def test_calc_prop_disk_area_two_rotors():
    area = calc_prop_disk_area_m2(11.61, 2)
    assert area == pytest.approx(2 * math.pi * (11.61 / 2) ** 2)


def test_calc_effective_disk_area_applies_blockage():
    assert calc_effective_disk_area_m2(100.0, 0.1) == pytest.approx(90.0)


def test_calc_ideal_static_thrust_matches_closed_form():
    p, rho, a = 1e6, 1.225, 50.0
    t = calc_ideal_static_thrust_n(p, rho, a)
    assert t == pytest.approx((p * p * 2 * rho * a) ** (1 / 3))


def test_calc_ideal_thrust_with_zero_speed_equals_static():
    p, rho, a = 2e6, 1.225, 100.0
    assert calc_ideal_thrust_with_axial_speed_n(p, rho, a, 0.0) == pytest.approx(
        calc_ideal_static_thrust_n(p, rho, a)
    )


def test_calc_ideal_thrust_decreases_with_forward_speed():
    p, rho, a = 9.18e6, 1.225, 210.0
    t0 = calc_ideal_thrust_with_axial_speed_n(p, rho, a, 0.0)
    t40 = calc_ideal_thrust_with_axial_speed_n(p, rho, a, 40.0)
    assert t40 < t0


def test_calc_propeller_thrust_applies_fm_and_blockage():
    p, rho, a = 1e6, 1.225, 50.0
    ideal = calc_ideal_static_thrust_n(p, rho, a * 0.9)
    actual = calc_propeller_thrust_n(p, rho, a, 0.0, figure_of_merit=0.8, nacelle_blockage_frac=0.1)
    assert actual == pytest.approx(0.8 * ideal)
