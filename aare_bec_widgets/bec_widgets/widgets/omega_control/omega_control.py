"""Omega rotation of the sample stage: readback, go-to, stop and preset moves on `aerotech.u`.

Why: on the beamline (pxii_bec device_configs/pxii-devices.yaml) omega is the `u` axis of the REST-driven
`aerotech` stage, i.e. a sub-signal of a composite device, not a Positioner, so BEC's PositionerBox refuses
it. SignalLabel does the readback, scans.mv accepts the dotted sub-device name for moves, and stop is the
same stop_devices message PositionerBox sends. Absolute presets are the axis' named positions from the
device config (userParameter.u: mount/work), so the lab's settings drive the buttons, not this file.
"""

from __future__ import annotations

from bec_lib.endpoints import MessageEndpoints
from bec_lib.messages import VariableMessage
from bec_widgets.utils.bec_widget import BECWidget
from bec_widgets.utils.error_popups import SafeSlot
from bec_widgets.widgets.utility.signal_label.signal_label import SignalLabel
from qtpy.QtCore import QLocale
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import QGridLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

# (label, degrees, relative). Absolute presets come from the device's userParameter at construction;
# override everything with `presets=` or set_presets() over RPC.
RELATIVE_PRESETS: list[tuple[str, float, bool]] = [
    (f"{sign * step:+d}", sign * step, True) for step in (10, 45, 90, 180) for sign in (1, -1)
]


class AareOmegaControl(BECWidget, QWidget):
    """Omega readback, go-to, stop and presets (named positions + +/-10 +/-45 +/-90 +/-180) for `aerotech.u`."""

    PLUGIN = True
    ICON_NAME = "rotate_right"
    USER_ACCESS = ["move_to", "move_by", "stop", "set_presets"]

    def __init__(
        self,
        parent=None,
        client=None,
        config=None,
        gui_id=None,
        device: str = "aerotech",
        axis: str = "u",
        presets: list[tuple[str, float, bool]] | None = None,
        **kwargs,
    ):
        super().__init__(parent=parent, client=client, config=config, gui_id=gui_id, **kwargs)
        self.get_bec_shortcuts()
        self.device = device
        self.axis = f"{device}.{axis}"  # dotted name: what scans.mv and self.dev[...] understand
        self.preset_buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Readback of the sub-signal `<device>_<axis>` from the device_readback stream of the root device.
        self.readback = SignalLabel(
            parent=self,
            client=self.client,
            device=device,
            signal=axis,
            show_select_button=False,
            custom_label="omega",
            custom_units="deg",
        )
        layout.addWidget(self.readback)

        row = QHBoxLayout()
        self.setpoint = QLineEdit(self)
        self.setpoint.setPlaceholderText("go to [deg] + Enter")
        validator = QDoubleValidator(self)
        validator.setLocale(QLocale.c())  # always "." as decimal point, whatever the desktop locale
        self.setpoint.setValidator(validator)
        self.setpoint.returnPressed.connect(lambda: self.move_to(float(self.setpoint.text())))
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop)
        row.addWidget(self.setpoint)
        row.addWidget(self.stop_button)
        layout.addLayout(row)

        self._preset_host = QWidget(self)
        self._preset_layout = QGridLayout(self._preset_host)
        layout.addWidget(self._preset_host)
        layout.addStretch()
        if presets is None:
            dev = self.dev.get(device)
            named = (dev.user_parameter.get(axis) if dev is not None else None) or {}
            presets = [(name, pos, False) for name, pos in named.items()] + RELATIVE_PRESETS
        self.set_presets(presets)

    @SafeSlot(list)
    def set_presets(self, presets: list[tuple[str, float, bool]]):
        """Rebuild the preset buttons from (label, degrees, relative) entries.

        Absolute presets take a full row, relative ones go two per row so +x/-x sit side by side."""
        for btn in self.preset_buttons:
            self._preset_layout.removeWidget(btn)
            btn.deleteLater()
        self.preset_buttons = []
        row = col = 0
        for label, degrees, relative in presets:
            btn = QPushButton(str(label), self._preset_host)
            btn.clicked.connect(
                lambda *_, d=float(degrees), r=relative: self.move_by(d) if r else self.move_to(d)
            )
            self.preset_buttons.append(btn)
            if relative:
                self._preset_layout.addWidget(btn, row, col)
                row, col = (row + 1, 0) if col else (row, 1)
            else:
                row += 1 if col else 0
                self._preset_layout.addWidget(btn, row, 0, 1, 2)
                row, col = row + 1, 0

    @SafeSlot(float, popup_error=True)
    def move_to(self, degrees: float):
        """Move omega to an absolute angle in degrees."""
        self.scans.mv(self.dev[self.axis], degrees, relative=False)

    @SafeSlot(float, popup_error=True)
    def move_by(self, degrees: float):
        """Rotate omega by `degrees` relative to the current position."""
        self.scans.mv(self.dev[self.axis], degrees, relative=True)

    @SafeSlot(popup_error=True)
    def stop(self):
        """Stop the stage. stop_devices works per root device, so this stops all aerotech axes.

        ponytail: pxii_bec's Aerotech controller.stop() is still a TODO upstream (no REST stop endpoint);
        the message is right, the hardware side lands with that fix."""
        self.client.connector.send(
            MessageEndpoints.stop_devices(), VariableMessage(value=[self.device])
        )


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    from aare_bec_widgets.bec_widgets.bluebird import apply_bluebird

    app = QApplication(sys.argv)
    apply_bluebird()
    widget = AareOmegaControl()
    widget.show()
    sys.exit(app.exec())
