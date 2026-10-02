"""Pure-math checks for the grid-scan control; the Qt side is exercised by hand in the RHEL9 container."""

from aare_bec_widgets.bec_widgets.widgets.grid_scan_control.grid_scan_control import (
    fmt_duration,
    grid_extent,
    grid_from_roi,
)


def test_grid_extent_is_centred_and_in_mm():
    # 10 µm pitch, 11 centres -> ±50 µm = ±0.05 mm
    assert grid_extent(10, 11) == (-0.05, 0.05)
    # a single element does not move
    assert grid_extent(10, 1) == (0.0, 0.0)


def test_fmt_duration_like_aaredaq():
    assert fmt_duration(0) == "0 min 0 s"
    assert fmt_duration(185.4) == "3 min 5 s"
    assert fmt_duration(59.6) == "1 min 0 s"  # rounding carries into minutes


def test_grid_from_roi_maps_pixels_to_elements_and_centre():
    # 200 x 120 px ROI at 1 µm/px with 10 µm pitch -> 20 x 12 elements;
    # centre 100 px right of the beam -> +0.1 mm, on the beam vertically -> 0 (y flipped by sign)
    assert grid_from_roi(220, 180, 420, 300, 10, 10, 1.0, -1.0, 220, 240) == (20, 12, 0.1, 0.0)
    # degenerate ROI still yields one element
    assert grid_from_roi(5, 5, 5, 5, 10, 10, 1.0, 1.0, 0, 0)[:2] == (1, 1)
