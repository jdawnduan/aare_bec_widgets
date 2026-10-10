"""Smargon omega rotation: readback/setpoint/stop via BEC's PositionerBox plus a row of preset moves.

Why: AareDAQ's goniometer use is mostly "rotate omega by a fixed angle"; PositionerBox already does the
readback, typed setpoint, tweak and stop, so this widget only adds the preset buttons on top of it.
"""

from __future__ import annotations

from bec_widgets.utils.bec_widget import BECWidget
from bec_widgets.utils.error_popups import SafeSlot
from bec_widgets.widgets.control.device_control.positioner_box import PositionerBox
from qtpy.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget

# (label, degrees, relative). Edit here, pass `presets=` to the widget, or call set_presets() over RPC.
DEFAULT_PRESETS: list[tuple[str, float, bool]] = [("0", 0, False)] + [
    (f"{sign * step:+d}", sign * step, True) for step in (10, 45, 90, 180) for sign in (1, -1)
]


class AareOmegaControl(BECWidget, QWidget):
    """Omega angle readback + presets (0 absolute, +/-10 +/-45 +/-90 +/-180 relative) for `smargon_omega`."""

    PLUGIN = True
    ICON_NAME = "rotate_right"
    USER_ACCESS = ["move_to", "move_by", "set_presets", "attach", "detach"]

    def __init__(
        self,
        parent=None,
        client=None,
        config=None,
        gui_id=None,
        device: str = "smargon_omega",
        presets: list[tuple[str, float, bool]] | None = None,
        **kwargs,
    ):
        super().__init__(parent=parent, client=client, config=config, gui_id=gui_id, **kwargs)
        self.get_bec_shortcuts()
        self.device = device
        self.preset_buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.box = PositionerBox(parent=self, client=self.client, device=device)
        self.box.hide_device_selection = True  # this widget is the omega axis, not a generic motor box
        # ponytail: SimPositioner reports egu "mm"; the omega axis is degrees. Fixed device, so set once.
        self.box.ui.units.setText("[deg]")
        layout.addWidget(self.box)

        self._preset_host = QWidget(self)
        self._preset_layout = QGridLayout(self._preset_host)
        layout.addWidget(self._preset_host)
        layout.addStretch()
        self.set_presets(presets if presets is not None else DEFAULT_PRESETS)

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
        self.scans.mv(self.dev[self.device], degrees, relative=False)

    @SafeSlot(float, popup_error=True)
    def move_by(self, degrees: float):
        """Rotate omega by `degrees` relative to the current position."""
        self.scans.mv(self.dev[self.device], degrees, relative=True)

    def cleanup(self):
        self.box.cleanup()
        super().cleanup()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    from aare_bec_widgets.bec_widgets.bluebird import apply_bluebird

    app = QApplication(sys.argv)
    apply_bluebird()
    widget = AareOmegaControl()
    widget.show()
    sys.exit(app.exec())
