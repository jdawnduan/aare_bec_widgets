"""AareOmegaControl against the fake BEC session; fixtures come from this folder's conftest.

The lab's omega is ``aerotech.u`` (sub-signal of the REST stage, BEC name ``aerotech_u``); the dev
loop uses a flat SimPositioner of the same name. Both spellings are covered here.
"""

from unittest import mock

import pytest
from bec_lib.device import Signal
from bec_lib.endpoints import MessageEndpoints
from bec_lib.messages import VariableMessage
from bec_widgets.tests.utils import FakeDevice, FakePositioner
from bec_widgets.utils.rpc_register import RPCRegister
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import QApplication, QPushButton

from aare_bec_widgets.bec_widgets.widgets.omega_control.omega_control import (
    DEFAULT_RELATIVE_PRESETS,
    AareOmegaControl,
    format_presets,
    parse_presets,
    resolve_axis,
)

try:
    from bec_widgets.tests.utils import create_widget
except ImportError:  # bec_widgets < 3.38 ships no helper (see conftest.py); same four lines

    def create_widget(qtbot, widget, *args, **kwargs):
        widget = widget(*args, **kwargs)
        qtbot.addWidget(widget)
        qtbot.waitExposed(widget)
        return widget


OMEGA = "aerotech_u"
NAMED = {"mount": 0, "work": 0}  # pxii-devices.yaml: aerotech.userParameter.u


@pytest.fixture
def omega_client(mocked_client):
    """The shared fake session plus the omega axis as the dev loop has it: a flat positioner."""
    axis = FakePositioner(OMEGA, limits=None, read_value=12.5)
    axis._config["userParameter"] = dict(NAMED)
    mocked_client.device_manager.add_devices([axis])
    return mocked_client


class FakeStage(FakeDevice):
    """FakeDevice plus the cached read the widget seeds from (FakePositioner has one, FakeDevice not)."""

    def read(self, cached=False):
        return self.signals


@pytest.fixture
def stage_client(mocked_client):
    """The beamline shape: `aerotech` root device with `u` as a plain sub-signal (no positioner)."""
    root = FakeStage("aerotech")
    root._config["userParameter"] = {"u": {"mount": 0, "work": 90, "tol": 0.01}, "x": {"in": 1}}
    root.u = Signal(name="u", parent=root)
    root.signals["aerotech_u"] = {"value": 45.0}
    mocked_client.device_manager.add_devices([root])
    return mocked_client


@pytest.fixture
def widget(qtbot, omega_client):
    return create_widget(qtbot, AareOmegaControl, client=omega_client)


@pytest.fixture
def mv(mocked_client):
    """Fresh mv mock per test: the fake client is a singleton and its auto-mock keeps old calls."""
    with mock.patch.object(mocked_client.scans, "mv") as patched:
        yield patched


def _button(widget, text):
    matches = [b for b in widget._preset_buttons if b.text() == text]
    assert len(matches) == 1, [b.text() for b in widget._preset_buttons]
    return matches[0]


def _wait_called(qtbot, mv):
    """The move runs through submit_task, so the mv mock is hit from the thread pool."""
    qtbot.waitUntil(lambda: mv.called, timeout=2000)
    return mv


def _wait_idle(qtbot, widget):
    """mv(...).wait() returned in the worker -> the completion slot reports idle."""
    qtbot.waitUntil(lambda: widget.status.text() == "idle", timeout=2000)


# -- pure helpers ---------------------------------------------------------------------------
def test_parse_presets_accepts_designer_string_and_lists():
    assert parse_presets("0, +10, -10") == [0.0, 10.0, -10.0]
    assert parse_presets("45;-45, ,") == [45.0, -45.0]
    assert parse_presets([1, "2", 3.5]) == [1.0, 2.0, 3.5]
    assert parse_presets(None) == []
    assert parse_presets("") == []


def test_format_presets_round_trips():
    assert format_presets([0.0, 10.0, -10.5]) == "0, 10, -10.5"
    assert parse_presets(format_presets(DEFAULT_RELATIVE_PRESETS)) == DEFAULT_RELATIVE_PRESETS


def test_resolve_axis_flat_then_dotted(omega_client, stage_client):
    dev = omega_client.device_manager.devices
    assert resolve_axis(dev, OMEGA) is dev[OMEGA]  # flat positioner wins when it exists
    del dev[OMEGA]
    assert resolve_axis(dev, OMEGA) is dev["aerotech"].u  # pxii motor_resolver fallback
    assert resolve_axis(dev, "aerotech.u") is dev["aerotech"].u
    assert resolve_axis(dev, "nope_u") is None


# -- readback -------------------------------------------------------------------------------
def test_initial_state_from_device(widget):
    assert widget.device == OMEGA
    assert widget.group.title() == OMEGA
    assert widget.readback.text() == "12.500 °"  # FakePositioner.precision == 3
    assert widget.status.text() == "idle"
    assert widget.go_button.isEnabled()
    assert widget.target.minimum() == -1e6  # no limits -> continuous rotation


def test_readback_slot_updates_angle_and_moving_flag(widget):
    widget.on_device_readback(
        {"signals": {OMEGA: {"value": 90.12345}, f"{OMEGA}_motor_is_moving": {"value": 1}}}, {}
    )
    assert widget.readback.text() == "90.123 °"
    assert widget.status.text() == "moving"
    widget.on_device_readback({"signals": {f"{OMEGA}_motor_done_move": {"value": 1}}}, {})
    assert widget.status.text() == "idle"  # EpicsMotor-style flag, checked first like PositionerBox
    widget.on_device_readback({"signals": {"samx": {"value": 1.0}}}, {})  # other device: no change
    assert widget.readback.text() == "90.123 °"


def test_readback_without_moving_flag_leaves_status_alone(widget):
    """EpicsMotor and the REST axis publish no moving flag: the angle updates, status does not."""
    widget.status.setText("go to 30 °")
    widget.on_device_readback({"signals": {OMEGA: {"value": 30.0}}}, {})
    assert widget.readback.text() == "30.000 °"
    assert widget.status.text() == "go to 30 °"


# -- beamline shape: aerotech.u ---------------------------------------------------------------
def test_sub_axis_of_the_rest_stage(qtbot, stage_client, mv, monkeypatch):
    connected = []
    w = create_widget(qtbot, AareOmegaControl, client=stage_client)
    monkeypatch.setattr(
        w.bec_dispatcher,
        "connect_slot",
        lambda slot, topics, cb_info=None, owner=None, **kwargs: connected.append(topics),
    )
    w.device = OMEGA  # re-target through the public path to observe the subscription
    assert connected[0].endpoint.endswith("/aerotech")  # root readback carries the sub-axis
    assert w._signal_key == "aerotech_u"
    assert w.readback.text() == "45.00 °"  # a bare Signal has no precision -> 2 decimals
    assert w.go_button.isEnabled()
    assert w.target.minimum() == -1e6  # a Signal has no limits
    # named positions come from aerotech.userParameter.u; `tol` is not an angle
    assert [b.text() for b in w._preset_buttons][:2] == ["mount 0°", "work 90°"]
    _button(w, "work 90°").click()
    _wait_called(qtbot, mv).assert_called_once_with(w.dev["aerotech"].u, 90.0, relative=False)
    _wait_idle(qtbot, w)


# -- moves ----------------------------------------------------------------------------------
def test_default_presets_render_as_buttons(widget):
    texts = [b.text() for b in widget._preset_buttons]
    assert texts == [
        "mount 0°",
        "work 0°",
        "+10°",
        "-10°",
        "+45°",
        "-45°",
        "+90°",
        "-90°",
        "+180°",
        "-180°",
    ]
    assert widget.absolute_presets == ""  # no hardcoded go-to angles besides the named ones
    assert widget.relative_presets == format_presets(DEFAULT_RELATIVE_PRESETS)


def test_relative_preset_click_steps_the_axis(widget, qtbot, mv):
    _button(widget, "-45°").click()
    assert widget.status.text() in ("step -45 °", "idle")
    _wait_called(qtbot, mv).assert_called_once_with(widget.dev[OMEGA], -45.0, relative=True)
    mv.return_value.wait.assert_called_once_with()
    _wait_idle(qtbot, widget)


def test_named_preset_click_goes_to_angle(widget, qtbot, mv):
    _button(widget, "mount 0°").click()
    _wait_called(qtbot, mv).assert_called_once_with(widget.dev[OMEGA], 0.0, relative=False)
    _wait_idle(qtbot, widget)


def test_go_button_moves_to_target(widget, qtbot, mv):
    widget.target.setValue(33.3)
    widget.go_button.click()
    _wait_called(qtbot, mv).assert_called_once_with(widget.dev[OMEGA], 33.3, relative=False)


def test_rpc_moves(widget, qtbot, mv):
    widget.move_relative(10)
    _wait_called(qtbot, mv).assert_called_once_with(widget.dev[OMEGA], 10.0, relative=True)
    mv.reset_mock()
    widget.move_absolute(180)
    _wait_called(qtbot, mv).assert_called_once_with(widget.dev[OMEGA], 180.0, relative=False)


def test_move_failure_lands_in_status(widget, qtbot, mv):
    mv.side_effect = RuntimeError("position=400 not within limits")
    widget.move_relative(400)
    qtbot.waitUntil(lambda: widget.status.text().startswith("move failed"), timeout=2000)
    assert "not within limits" in widget.status.text()


def test_wait_failure_lands_in_status(widget, qtbot, mv):
    """The request is accepted but the axis fails underway (REST / ECMC error): wait() raises."""
    mv.return_value.wait.side_effect = RuntimeError("Motor reported ECMC error 'HW_ERROR'")
    widget.move_absolute(90)
    qtbot.waitUntil(lambda: widget.status.text().startswith("move failed"), timeout=2000)
    assert "HW_ERROR" in widget.status.text()


def test_stop_sends_stop_devices_for_root(widget):
    with mock.patch.object(widget.client.connector, "send") as send:
        widget.stop()
    send.assert_called_once_with(MessageEndpoints.stop_devices(), VariableMessage(value=[OMEGA]))
    assert widget.status.text() == "stop requested"


def test_limits_clamp_the_target_spinbox(qtbot, mocked_client):
    w = create_widget(qtbot, AareOmegaControl, client=mocked_client, device="samx")  # [-10, 10]
    assert (w.target.minimum(), w.target.maximum()) == (-10.0, 10.0)
    w.device = "aptrx"  # limits None -> unlimited again
    assert (w.target.minimum(), w.target.maximum()) == (-1e6, 1e6)


# -- configuration --------------------------------------------------------------------------
def test_presets_configurable_at_runtime(widget):
    widget.relative_presets = "5, -5"
    widget.absolute_presets = [0, 90]
    assert widget.relative_presets == "5, -5"
    assert widget.absolute_presets == "0, 90"
    assert widget.config.relative_presets == [5.0, -5.0]
    assert [b.text() for b in widget._preset_buttons] == [
        "mount 0°",
        "work 0°",
        "0°",
        "90°",
        "+5°",
        "-5°",
    ]
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert len(widget.findChildren(QPushButton)) == 2 + 6  # go, stop + presets; old ones gone
    widget.absolute_presets = ""
    assert not widget.absolute_host.isHidden()  # named positions keep the row
    widget.relative_presets = ""
    assert widget.relative_host.isHidden()


def test_presets_from_constructor(qtbot, omega_client):
    w = create_widget(
        qtbot, AareOmegaControl, client=omega_client, absolute_presets="", relative_presets=[1, -1]
    )
    assert w.config.absolute_presets == []
    assert w.config.relative_presets == [1.0, -1.0]
    assert [b.text() for b in w._preset_buttons] == ["mount 0°", "work 0°", "+1°", "-1°"]


def test_config_dict_is_accepted(qtbot, omega_client):
    w = create_widget(
        qtbot,
        AareOmegaControl,
        client=omega_client,
        config={"device": "samx", "relative_presets": [2]},
    )
    assert w.device == "samx"
    assert w.group.title() == "samx"
    assert w.relative_presets == "2"
    assert [b.text() for b in w._preset_buttons] == ["+2°"]  # samx has no named positions
    assert w.absolute_host.isHidden()


def test_set_device_swaps_subscription(widget, monkeypatch):
    disconnected, connected = [], []
    monkeypatch.setattr(
        widget.bec_dispatcher,
        "disconnect_slot",
        lambda slot, topics, cb_info=None: disconnected.append(topics),
    )
    monkeypatch.setattr(
        widget.bec_dispatcher,
        "connect_slot",
        lambda slot, topics, cb_info=None, owner=None, **kwargs: connected.append(topics),
    )
    widget.device = "samx"
    assert widget.config.device == "samx"
    assert disconnected[0].endpoint.endswith(OMEGA)
    assert connected[0].endpoint.endswith("samx")
    assert widget.group.title() == "samx"
    assert widget.readback.text() == "2.000 °"  # samx read value in the shared fake session


def test_unknown_device_keeps_widget_alive_but_parked(qtbot, mocked_client, mv):
    w = create_widget(qtbot, AareOmegaControl, client=mocked_client)  # no aerotech loaded
    assert w.readback.text() == "n/a"
    assert not w.go_button.isEnabled()
    assert not w._preset_buttons[0].isEnabled()
    with pytest.raises(RuntimeError):
        w.move_relative(10, _override_slot_params={"raise_error": True})
    mv.assert_not_called()

    w.device = "samx"  # axis appears / user re-targets: panel comes alive
    assert w.go_button.isEnabled()
    assert w._preset_buttons[0].isEnabled()
    assert w.readback.text() == "2.000 °"

    w.device = "bpm4i"  # a plain detector is not movable: parked again
    assert not w.go_button.isEnabled()


def test_user_access_entries_exist():
    for name in AareOmegaControl.USER_ACCESS:
        assert hasattr(AareOmegaControl, name.removesuffix(".setter")), name


def test_apply_theme_colors_buttons(widget):
    widget.apply_theme("dark")
    assert "color:" in widget.go_button.styleSheet()
    assert "color:" in widget.stop_button.styleSheet()


def test_close_runs_cleanup_once_and_unregisters(omega_client, monkeypatch):
    w = AareOmegaControl(client=omega_client)
    gui_id = w.gui_id
    assert RPCRegister().get_rpc_by_id(gui_id) is w
    calls = []
    original = w.cleanup
    monkeypatch.setattr(w, "cleanup", lambda: (calls.append(1), original()))

    w.close()
    assert w._destroyed is True
    assert calls == [1]
    assert RPCRegister().get_rpc_by_id(gui_id) is None

    w.close()  # idempotent
    w.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    assert calls == [1]
