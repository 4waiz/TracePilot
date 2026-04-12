"""
Unit tests for the tolerance checking engine.

The core logic: a measurement passes when lower_limit <= actual_value <= upper_limit.
This mirrors the deterministic check in backend/routers/inspection_routes.py.
"""


def check_tolerance(actual_value: float, lower_limit: float, upper_limit: float) -> bool:
    """Pure tolerance check extracted from the inspection logic."""
    return lower_limit <= actual_value <= upper_limit


# ── Outer Diameter spec: nominal 25.400, ±0.013 ────────────────────────────
OD_LOWER = 25.387
OD_UPPER = 25.413


def test_pass_within_tolerance():
    """Value comfortably within limits should pass."""
    assert check_tolerance(25.400, OD_LOWER, OD_UPPER) is True
    assert check_tolerance(25.395, OD_LOWER, OD_UPPER) is True
    assert check_tolerance(25.410, OD_LOWER, OD_UPPER) is True


def test_fail_above_upper_limit():
    """Value above the upper limit should fail."""
    assert check_tolerance(25.414, OD_LOWER, OD_UPPER) is False
    assert check_tolerance(25.500, OD_LOWER, OD_UPPER) is False


def test_fail_below_lower_limit():
    """Value below the lower limit should fail."""
    assert check_tolerance(25.386, OD_LOWER, OD_UPPER) is False
    assert check_tolerance(25.000, OD_LOWER, OD_UPPER) is False


def test_pass_at_exact_lower_limit():
    """Value exactly at the lower boundary should pass (inclusive)."""
    assert check_tolerance(25.387, OD_LOWER, OD_UPPER) is True


def test_pass_at_exact_upper_limit():
    """Value exactly at the upper boundary should pass (inclusive)."""
    assert check_tolerance(25.413, OD_LOWER, OD_UPPER) is True


def test_pass_nominal_value():
    """Nominal value should always pass."""
    # Outer Diameter
    assert check_tolerance(25.400, OD_LOWER, OD_UPPER) is True
    # Bore Diameter (asymmetric: +0.018/-0.000)
    assert check_tolerance(10.000, 10.000, 10.018) is True
    # Overall Length
    assert check_tolerance(150.000, 149.950, 150.050) is True
    # Thread Pitch Diameter
    assert check_tolerance(12.700, 12.675, 12.725) is True
    # Surface Finish Ra
    assert check_tolerance(0.800, 0.000, 1.600) is True
