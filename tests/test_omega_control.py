"""AareOmegaControl against a fake of the beamline's `aerotech` stage: readback of `u`, presets, moves, stop."""

from unittest import mock

import pytest
from bec_lib.endpoints import MessageEndpoints
from bec_widgets.tests.utils import FakeDevice

from aare_bec_widgets.bec_widgets.widgets.omega_control.omega_control import (
    RELATIVE_PRESETS,
    AareOmegaControl,
)


class FakeAerotech(FakeDevice):
    """Shape of pxii-devices.yaml `aerotech`: omega is the sub-signal `u`, named positions in userParameter."""

    def __init__(self, angle: float = 12.5):
        super().__init__("aerotech")
        self._info["signals"]["u"] = {
            "kind_str": "normal",
            "component_name": "u",
            "obj_name": "aerotech_u",
            "describe": {"dtype": "float"},
        }
        self._parse_info()  # builds self.u the way the real client does from device info
        self._config["userParameter"] = {"u": {"mount": 0, "work": 0}}
        self.signals = {"aerotech_u": {"value": angle}}

    def read(self, cached=False):
        return self.signals

    def read_configuration(self, cached=False):
        return {}  # SignalLabel reads it too; the fake has no connector behind it


@pytest.fixture
def widget(qtbot, mocked_client):
    mocked_client.device_manager.add_devices([FakeAerotech()])
    w = AareOmegaControl(client=mocked_client)
    qtbot.addWidget(w)
    qtbot.waitExposed(w)
    yield w
    w.close()


def test_readback_and_presets_follow_device_config(widget):
    assert widget.readback._display.text() == "12.500 deg"
    assert [b.text() for b in widget.preset_buttons] == ["mount", "work"] + [
        p[0] for p in RELATIVE_PRESETS
    ]


def test_moves_target_the_omega_sub_signal(widget):
    buttons = {b.text(): b for b in widget.preset_buttons}
    omega = widget.dev["aerotech.u"]
    buttons["+45"].click()
    widget.scans.mv.assert_called_with(omega, 45.0, relative=True)
    buttons["mount"].click()
    widget.scans.mv.assert_called_with(omega, 0.0, relative=False)
    widget.setpoint.setText("90")
    widget.setpoint.returnPressed.emit()
    widget.scans.mv.assert_called_with(omega, 90.0, relative=False)


def test_stop_sends_stop_devices_for_root_device(widget):
    with mock.patch.object(widget.client.connector, "send") as send:
        widget.stop_button.click()
    endpoint, msg = send.call_args.args
    assert endpoint == MessageEndpoints.stop_devices()
    assert msg.value == ["aerotech"]


def test_set_presets_rebuilds_buttons(widget):
    widget.set_presets([("+30", 30, True), ("home", 0, False)])
    assert [b.text() for b in widget.preset_buttons] == ["+30", "home"]
    widget.preset_buttons[1].click()
    widget.scans.mv.assert_called_with(widget.dev["aerotech.u"], 0.0, relative=False)
