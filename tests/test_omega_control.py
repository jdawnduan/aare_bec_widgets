"""AareOmegaControl: presets, readback and the move calls behind each button."""

import pytest
from bec_widgets.tests.utils import FakePositioner

from aare_bec_widgets.bec_widgets.widgets.omega_control.omega_control import (
    DEFAULT_PRESETS,
    AareOmegaControl,
)


@pytest.fixture
def widget(qtbot, mocked_client):
    # the shared fake devices have no smargon_omega; add one at a known angle
    mocked_client.device_manager.add_devices([FakePositioner("smargon_omega", read_value=12.5)])
    w = AareOmegaControl(client=mocked_client)
    qtbot.addWidget(w)
    qtbot.waitExposed(w)
    yield w
    w.close()


def test_default_presets_match_spec():
    assert DEFAULT_PRESETS == [
        ("0", 0, False),
        ("+10", 10, True),
        ("-10", -10, True),
        ("+45", 45, True),
        ("-45", -45, True),
        ("+90", 90, True),
        ("-90", -90, True),
        ("+180", 180, True),
        ("-180", -180, True),
    ]


def test_shows_omega_readback_in_degrees(widget):
    assert widget.box.device == "smargon_omega"
    assert float(widget.box.ui.readback.text()) == 12.5
    assert widget.box.ui.units.text() == "[deg]"
    assert [b.text() for b in widget.preset_buttons] == [p[0] for p in DEFAULT_PRESETS]


def test_preset_buttons_move_absolute_or_relative(widget):
    buttons = {b.text(): b for b in widget.preset_buttons}
    omega = widget.dev["smargon_omega"]
    buttons["+45"].click()
    widget.scans.mv.assert_called_with(omega, 45.0, relative=True)
    buttons["0"].click()
    widget.scans.mv.assert_called_with(omega, 0.0, relative=False)


def test_set_presets_rebuilds_buttons(widget):
    widget.set_presets([("+30", 30, True), ("home", 0, False)])
    assert [b.text() for b in widget.preset_buttons] == ["+30", "home"]
    widget.preset_buttons[1].click()
    widget.scans.mv.assert_called_with(widget.dev["smargon_omega"], 0.0, relative=False)
