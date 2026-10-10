"""SMARGON omega rotation: live angle of ``smargon_omega`` plus go-to, stop and preset moves.

Why: during crystal alignment the omega row (angle readout, go-to, +/- step buttons) is the control
users hit most, so it gets a compact panel of its own instead of the generic PositionerBox. The
presets are plain lists in the widget config, exposed as Qt properties, so a beamline changes them
from Qt Designer, the constructor or the RPC client without touching code.
"""

from __future__ import annotations

from bec_lib.device import Positioner
from bec_lib.endpoints import MessageEndpoints
from bec_lib.logger import bec_logger
from bec_lib.messages import VariableMessage
from bec_widgets.utils.bec_connector import ConnectionConfig
from bec_widgets.utils.bec_widget import BECWidget
from bec_widgets.utils.colors import get_accent_colors
from bec_widgets.utils.error_popups import SafeProperty, SafeSlot
from pydantic import Field
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = bec_logger.logger

DEFAULT_ABSOLUTE_PRESETS = [0.0]
DEFAULT_RELATIVE_PRESETS = [10.0, -10.0, 45.0, -45.0, 90.0, -90.0, 180.0, -180.0]
# Relative preset buttons per row: the eight defaults become two rows that fit a narrow dock.
PRESET_COLUMNS = 4


def parse_presets(value: str | list | tuple | None) -> list[float]:
    """``"0, +10, -10"`` (Qt Designer / RPC string) or ``[0, 10, -10]`` -> ``[0.0, 10.0, -10.0]``."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    return [float(v) for v in value if str(v).strip()]


def format_presets(values: list[float]) -> str:
    """Inverse of parse_presets: ``[0.0, 10.0, -10.0]`` -> ``"0, 10, -10"``."""
    return ", ".join(f"{v:g}" for v in values)


class AareOmegaControlConfig(ConnectionConfig):
    """Persisted widget settings: the device and the two preset lists (degrees)."""

    device: str = Field("smargon_omega", description="Positioner driven by the widget.")
    absolute_presets: list[float] = Field(
        default_factory=lambda: list(DEFAULT_ABSOLUTE_PRESETS), description="Go-to angles."
    )
    relative_presets: list[float] = Field(
        default_factory=lambda: list(DEFAULT_RELATIVE_PRESETS),
        description="Step angles, relative to the current position.",
    )


class AareOmegaControl(BECWidget, QWidget):
    """Omega rotation of the SMARGON goniometer: live angle, go-to, stop and preset moves."""

    PLUGIN = True
    ICON_NAME = "rotate_right"
    USER_ACCESS = [
        *BECWidget.USER_ACCESS,
        "device",
        "device.setter",
        "absolute_presets",
        "absolute_presets.setter",
        "relative_presets",
        "relative_presets.setter",
        "move_absolute",
        "move_relative",
        "stop",
    ]

    def __init__(
        self,
        parent: QWidget | None = None,
        client=None,
        config: AareOmegaControlConfig | dict | None = None,
        gui_id: str | None = None,
        device: str | None = None,
        absolute_presets: str | list[float] | None = None,
        relative_presets: str | list[float] | None = None,
        **kwargs,
    ):
        if config is None:
            config = AareOmegaControlConfig(widget_class=self.__class__.__name__)
        elif isinstance(config, dict):
            config = AareOmegaControlConfig(**config)
        super().__init__(parent=parent, client=client, config=config, gui_id=gui_id, **kwargs)
        self.config: AareOmegaControlConfig
        self.get_bec_shortcuts()

        self._readback_endpoint = None
        self._precision = 2
        self._device_ok = False
        self._preset_buttons: list[QPushButton] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.group = QGroupBox(self.config.device, self)
        outer.addWidget(self.group)
        outer.addStretch()
        layout = QGridLayout(self.group)
        layout.setColumnStretch(1, 1)

        self.readback = QLabel("-", self.group)
        self.readback.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        font = self.readback.font()
        font.setPointSize(font.pointSize() + 6)
        font.setBold(True)
        self.readback.setFont(font)
        self.status = QLabel("", self.group)
        layout.addWidget(QLabel("Omega", self.group), 0, 0)
        layout.addWidget(self.readback, 0, 1)
        layout.addWidget(self.status, 0, 2)

        self.target = QDoubleSpinBox(self.group)
        self.target.setRange(-1e6, 1e6)  # the device enforces its limits, the widget does not guess
        self.target.setSuffix(" °")
        self.target.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.go_button = QPushButton("Go", self.group)
        self.stop_button = QPushButton("Stop", self.group)
        buttons = QHBoxLayout()
        buttons.addWidget(self.go_button)
        buttons.addWidget(self.stop_button)
        layout.addWidget(QLabel("Target", self.group), 1, 0)
        layout.addWidget(self.target, 1, 1)
        layout.addLayout(buttons, 1, 2)

        self.absolute_label = QLabel("Go to", self.group)
        self.absolute_host = QWidget(self.group)
        self._absolute_layout = QHBoxLayout(self.absolute_host)
        self._absolute_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.absolute_label, 2, 0)
        layout.addWidget(self.absolute_host, 2, 1, 1, 2)

        self.relative_label = QLabel("Step", self.group)
        self.relative_host = QWidget(self.group)
        self._relative_layout = QGridLayout(self.relative_host)
        self._relative_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.relative_label, 3, 0)
        layout.addWidget(self.relative_host, 3, 1, 1, 2)

        self.go_button.clicked.connect(self._on_go_clicked)
        self.stop_button.clicked.connect(self.stop)

        if absolute_presets is not None:
            self.config.absolute_presets = parse_presets(absolute_presets)
        if relative_presets is not None:
            self.config.relative_presets = parse_presets(relative_presets)
        self._rebuild_presets()
        self.device = device or self.config.device

    # ------------------------------------------------------------------ device
    @SafeProperty(str)
    def device(self) -> str:
        """Positioner driven by the widget (default: smargon_omega)."""
        return self.config.device

    @device.setter
    def device(self, device: str) -> None:
        # Re-targeting and the first subscription share this path. No cleanup() override is needed:
        # BECWidget.cleanup() releases every subscription this widget owns.
        if self._readback_endpoint is not None:
            self.bec_dispatcher.disconnect_slot(self.on_device_readback, self._readback_endpoint)
        self.config.device = device
        self.group.setTitle(device)
        self._readback_endpoint = MessageEndpoints.device_readback(device)
        self.bec_dispatcher.connect_slot(self.on_device_readback, self._readback_endpoint)
        self._init_from_device()

    def _init_from_device(self) -> None:
        """Seed angle and precision from the device; park the controls if it is not a positioner."""
        device = self.config.device
        self._device_ok = device in self.dev and isinstance(self.dev[device], Positioner)
        if not self._device_ok:
            # No raise: a GUI started before the device config was loaded must still come up.
            # Setting `device` again (RPC, Designer) once the positioner exists revives the panel.
            logger.warning(f"{device} is not a positioner in the current session")
            self.readback.setText("n/a")
            self.status.setText("not a positioner in this session")
            self._set_controls_enabled(False)
            return
        try:
            self._precision = int(getattr(self.dev[device], "precision", 2))
        except (TypeError, ValueError):
            self._precision = 2
        self.target.setDecimals(self._precision)
        self.status.setText("")
        self._set_controls_enabled(True)
        self.on_device_readback({"signals": self.dev[device].read(cached=True)}, {})

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in (self.target, self.go_button, self.stop_button, *self._preset_buttons):
            widget.setEnabled(enabled)

    # ------------------------------------------------------------------ readback
    @SafeSlot(dict, dict)
    def on_device_readback(self, content: dict, metadata: dict) -> None:
        """Dispatcher slot for MessageEndpoints.device_readback(device): angle and moving flag."""
        signals = content.get("signals", {})
        device = self.config.device
        value = signals.get(device, {}).get("value")
        if value is not None:
            self.readback.setText(f"{value:.{self._precision}f} °")
        moving = signals.get(f"{device}_motor_is_moving", {}).get("value")
        if moving is not None:
            self.status.setText("moving" if moving else "idle")

    # ------------------------------------------------------------------ moves
    @SafeSlot(float, popup_error=True)
    def move_absolute(self, angle: float) -> None:
        """Rotate to ``angle``.

        Args:
            angle (float): target angle in degrees.
        """
        self._move(float(angle), relative=False)

    @SafeSlot(float, popup_error=True)
    def move_relative(self, delta: float) -> None:
        """Rotate by ``delta`` from the current position.

        Args:
            delta (float): signed step in degrees.
        """
        self._move(float(delta), relative=True)

    @SafeSlot(popup_error=True)
    def stop(self) -> None:
        """Stop the rotation (same stop_devices message as BEC's PositionerBox)."""
        self.client.connector.send(
            MessageEndpoints.stop_devices(), VariableMessage(value=[self.config.device])
        )
        self.status.setText("stop requested")

    def _move(self, value: float, relative: bool) -> None:
        device = self.config.device
        if not self._device_ok:
            raise RuntimeError(f"{device} is not a positioner in the current session")
        self.status.setText(f"step {value:+g} °" if relative else f"go to {value:g} °")
        # scans.mv builds the request from the device info and sends it to Redis. Off the GUI
        # thread so a stalled connector never freezes the panel; failures arrive via on_failed.
        self.submit_task(
            self.scans.mv,
            self.dev[device],
            value,
            relative=relative,
            on_failed=self._on_move_failed,
        )

    @SafeSlot()
    def _on_go_clicked(self) -> None:
        self.move_absolute(self.target.value())

    @SafeSlot(str)
    def _on_move_failed(self, traceback_text: str) -> None:
        # The worker already logged the full traceback; the user gets the last line.
        lines = [line for line in traceback_text.strip().splitlines() if line.strip()]
        self.status.setText(f"move failed: {lines[-1] if lines else 'unknown error'}")

    # ------------------------------------------------------------------ presets
    @SafeProperty(str)
    def absolute_presets(self) -> str:
        """Go-to angles in degrees, comma separated (``"0, 90"``); a list is accepted when setting."""
        return format_presets(self.config.absolute_presets)

    @absolute_presets.setter
    def absolute_presets(self, value: str | list[float]) -> None:
        self.config.absolute_presets = parse_presets(value)
        self._rebuild_presets()

    @SafeProperty(str)
    def relative_presets(self) -> str:
        """Step angles in degrees, comma separated (``"10, -10"``); a list is accepted when setting."""
        return format_presets(self.config.relative_presets)

    @relative_presets.setter
    def relative_presets(self, value: str | list[float]) -> None:
        self.config.relative_presets = parse_presets(value)
        self._rebuild_presets()

    def _rebuild_presets(self) -> None:
        for button in self._preset_buttons:
            button.hide()
            button.deleteLater()  # the layout drops the item when the widget is destroyed
        self._preset_buttons = []
        for angle in self.config.absolute_presets:
            button = self._preset_button(f"{angle:g}°", f"Go to {angle:g}°")
            button.clicked.connect(lambda *_, a=angle: self.move_absolute(a))
            self._absolute_layout.addWidget(button)
        for index, delta in enumerate(self.config.relative_presets):
            button = self._preset_button(f"{delta:+g}°", f"Step by {delta:+g}°")
            button.clicked.connect(lambda *_, d=delta: self.move_relative(d))
            self._relative_layout.addWidget(button, index // PRESET_COLUMNS, index % PRESET_COLUMNS)
        for label, host, presets in (
            (self.absolute_label, self.absolute_host, self.config.absolute_presets),
            (self.relative_label, self.relative_host, self.config.relative_presets),
        ):
            label.setVisible(bool(presets))
            host.setVisible(bool(presets))

    def _preset_button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text, self.group)
        button.setToolTip(tooltip)
        button.setEnabled(self._device_ok)
        self._preset_buttons.append(button)
        return button

    # ------------------------------------------------------------------ theme
    def apply_theme(self, theme: str) -> None:
        accent = get_accent_colors()
        self.go_button.setStyleSheet(f"color: {accent.success.name()};")
        self.stop_button.setStyleSheet(f"color: {accent.emergency.name()};")


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    from aare_bec_widgets.bec_widgets.bluebird import apply_bluebird

    app = QApplication(sys.argv)
    apply_bluebird()  # standalone dev loop shows the same theme bec-app runs with
    widget = AareOmegaControl()
    widget.show()
    sys.exit(app.exec())
