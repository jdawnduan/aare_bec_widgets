"""Grid-scan control in the AareDAQ "Raster data collection" layout, driving BEC's grid_scan.

Why: the plugin repo shipped no real widget. This is the reference for mapping an AareDAQ panel onto
a BECWidget: layout, wording and colors follow
aare_suite/AareDAQ/src/aare/gui/panels/raster_data_collection.py (label | value x value | unit grid,
banner title, green Go / red Abort). Camera-only rows (metric, transparency, grid table, X-ray
centering) are left out: BEC has no sample-camera overlay to draw the grid on, so the grid is typed in.
"""

from __future__ import annotations

from bec_lib.endpoints import MessageEndpoints
from bec_widgets.utils.bec_widget import BECWidget
from bec_widgets.utils.colors import get_accent_colors, get_theme_name
from bec_widgets.utils.error_popups import SafeSlot
from bec_widgets.widgets.control.device_input.device_combobox.device_combobox import (
    BECDeviceFilter,
    DeviceComboBox,
)
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# AareDAQ TitleLabel banner (styles.py: BANNER/BANNER_TEXT light, DARK_ELEVATED/DARK_ACCENT dark).
# Hex literals because bec_qthemes has no banner role to read them from.
_BANNER_QSS = {
    "light": "background-color: #a2b7e4; color: #F8F8FC; border-color: #ffffff;",
    "dark": "background-color: #253148; color: #e0913f; border-color: #e0913f;",
}


def grid_extent(pitch_um: float, n: int) -> tuple[float, float]:
    """Relative start/stop in mm for n element centres `pitch_um` apart, centred on the current position."""
    half = pitch_um * (n - 1) / 2 / 1000.0
    return -half, half


def grid_from_roi(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    pitch_x_um: float,
    pitch_y_um: float,
    um_per_px_x: float,
    um_per_px_y: float,
    beam_cx: float,
    beam_cy: float,
) -> tuple[int, int, float, float]:
    """ROI corners in image pixels -> (n_x, n_y, centre_dx_mm, centre_dy_mm) relative to the beam position.

    Same job as AareDAQ RasterGridManager.update_active_grid: element count from the drawn size and the
    element pitch, grid centre as a motor offset from the beam mark."""
    n_x = max(1, round(abs(x1 - x0) * abs(um_per_px_x) / pitch_x_um))
    n_y = max(1, round(abs(y1 - y0) * abs(um_per_px_y) / pitch_y_um))
    dx_mm = ((x0 + x1) / 2 - beam_cx) * um_per_px_x / 1000.0
    dy_mm = ((y0 + y1) / 2 - beam_cy) * um_per_px_y / 1000.0
    return n_x, n_y, dx_mm, dy_mm


def fmt_duration(seconds: float) -> str:
    """'3 min 5 s' like AareDAQ's measurement-time readout."""
    mins, secs = divmod(round(seconds), 60)
    return f"{mins} min {secs} s"


class AareGridScanControl(BECWidget, QWidget):
    """Raster (grid) scan control: two motors, element pitch, image time, grid elements -> scans.grid_scan."""

    PLUGIN = True
    ICON_NAME = "grid_on"
    USER_ACCESS = ["run", "abort", "set_grid_from_pixels", "attach", "detach"]

    def __init__(self, parent=None, client=None, config=None, gui_id=None, **kwargs):
        super().__init__(parent=parent, client=client, config=config, gui_id=gui_id, **kwargs)
        self.get_bec_shortcuts()
        # grid centre as motor offset from the current position (mm); (0, 0) until a ROI was drawn
        self._center_mm = (0.0, 0.0)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.banner = QLabel("Raster data collection", self)
        self.banner.setObjectName("aareBanner")
        self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner.setFixedHeight(25)
        outer.addWidget(self.banner)

        grid_host = QWidget(self)
        self._layout = QGridLayout(grid_host)
        self._layout.setColumnStretch(1, 1)
        self._layout.setColumnStretch(3, 1)
        outer.addWidget(grid_host)
        outer.addStretch()

        pos = BECDeviceFilter.POSITIONER
        self.motor_x = DeviceComboBox(self, client=self.client, device_filter=pos, default="samx")
        self.motor_y = DeviceComboBox(self, client=self.client, device_filter=pos, default="samy")
        self._add_pair_row(0, "Motors", self.motor_x, self.motor_y)

        self.size_x = self._spin(5, 100, 10, decimals=0)
        self.size_y = self._spin(5, 100, 10, decimals=0)
        self._add_pair_row(1, "Grid element size", self.size_x, self.size_y, "μm")

        self.exp_time = self._spin(0.0005, 10.0, 0.1, decimals=4)
        self._add_row(2, "Image time", self.exp_time, "s")

        self.n_x = QSpinBox(self)
        self.n_y = QSpinBox(self)
        for box in (self.n_x, self.n_y):
            box.setRange(1, 500)
            box.setValue(10)
            box.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._add_pair_row(3, "Grid elements", self.n_x, self.n_y)

        self.grid_size_x = QLabel("-", self)
        self.grid_size_y = QLabel("-", self)
        self._add_pair_row(4, "Grid size", self.grid_size_x, self.grid_size_y, "μm")

        self.center_x = QLabel("0.0", self)
        self.center_y = QLabel("0.0", self)
        self._add_pair_row(5, "Grid centre", self.center_x, self.center_y, "μm")

        self.total_time = QLabel("-", self)
        self._add_row(6, "Measurement time", self.total_time)

        self.status = QLabel("idle", self)
        self._add_row(7, "Status", self.status)

        self.start_button = QPushButton("Evaluate grid", self)
        self.start_button.clicked.connect(self.run)
        self._layout.addWidget(self.start_button, 8, 0, 1, 5)

        self.abort_button = QPushButton("Abort measurement", self)
        self.abort_button.clicked.connect(self.abort)
        self._layout.addWidget(self.abort_button, 9, 0, 1, 5)

        for box in (self.size_x, self.size_y, self.exp_time, self.n_x, self.n_y):
            box.valueChanged.connect(self._update_readouts)
        self._update_readouts()

        self.bec_dispatcher.connect_slot(self.on_scan_progress, MessageEndpoints.scan_progress())
        self.apply_theme(get_theme_name())

    # -- layout helpers (same grid shape as AareDAQ's ScanSettingsPanel) ----------------------
    def _spin(self, lo: float, hi: float, value: float, decimals: int) -> QDoubleSpinBox:
        box = QDoubleSpinBox(self)
        box.setDecimals(decimals)
        box.setRange(lo, hi)
        box.setValue(value)
        box.setAlignment(Qt.AlignmentFlag.AlignRight)
        return box

    def _add_row(self, row: int, label: str, field: QWidget, unit: str = "") -> None:
        self._layout.addWidget(QLabel(label, self), row, 0)
        self._align_readout(field)
        self._layout.addWidget(field, row, 1, 1, 3)
        if unit:
            self._layout.addWidget(QLabel(unit, self), row, 4)

    def _add_pair_row(self, row: int, label: str, first: QWidget, second: QWidget, unit: str = ""):
        self._layout.addWidget(QLabel(label, self), row, 0)
        self._layout.addWidget(QLabel(" x ", self), row, 2)
        for widget, column in ((first, 1), (second, 3)):
            self._align_readout(widget)
            self._layout.addWidget(widget, row, column)
        if unit:
            self._layout.addWidget(QLabel(unit, self), row, 4)

    @staticmethod
    def _align_readout(widget: QWidget) -> None:
        if isinstance(widget, QLabel):
            widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    # -- readouts ----------------------------------------------------------------------------
    @SafeSlot()
    def _update_readouts(self, *_):
        self.grid_size_x.setText(f"{self.size_x.value() * self.n_x.value():.1f}")
        self.grid_size_y.setText(f"{self.size_y.value() * self.n_y.value():.1f}")
        # 30 % buffer, as AareDAQ's calculate_total_time
        points = self.n_x.value() * self.n_y.value()
        self.total_time.setText(fmt_duration(points * self.exp_time.value() * 1.3))

    @SafeSlot(float, float, float, float, float, float, float, float)
    def set_grid_from_pixels(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        um_per_px_x: float = 1.0,
        um_per_px_y: float = 1.0,
        beam_cx: float = 0.0,
        beam_cy: float = 0.0,
    ):
        """Take the grid from a rectangle drawn on the camera image (see AareRasterPanel)."""
        n_x, n_y, dx, dy = grid_from_roi(
            x0,
            y0,
            x1,
            y1,
            self.size_x.value(),
            self.size_y.value(),
            um_per_px_x,
            um_per_px_y,
            beam_cx,
            beam_cy,
        )
        self._center_mm = (dx, dy)
        self.n_x.setValue(n_x)
        self.n_y.setValue(n_y)
        # + 0.0 turns a tiny negative into 0.0 instead of "-0.0"
        self.center_x.setText(f"{round(dx * 1000, 1) + 0.0:.1f}")
        self.center_y.setText(f"{round(dy * 1000, 1) + 0.0:.1f}")

    @SafeSlot(dict, dict)
    def on_scan_progress(self, msg_content: dict, metadata: dict):
        if msg_content.get("done"):
            self.status.setText("done")
        else:
            self.status.setText(
                f"running {msg_content.get('value', 0):.0f}/{msg_content.get('max_value', 0):.0f}"
            )

    # -- actions -----------------------------------------------------------------------------
    @SafeSlot(popup_error=True)
    def run(self):
        """Start the grid scan, centred on the current motor positions (relative, snaked)."""
        cx, cy = self._center_mm  # ROI-picked grid centre, (0, 0) when typed in
        x0, x1 = grid_extent(self.size_x.value(), self.n_x.value())
        y0, y1 = grid_extent(self.size_y.value(), self.n_y.value())
        self.status.setText("queued")
        self.scans.grid_scan(
            self.dev[self.motor_x.currentText()],
            cx + x0,
            cx + x1,
            self.n_x.value(),
            self.dev[self.motor_y.currentText()],
            cy + y0,
            cy + y1,
            self.n_y.value(),
            exp_time=self.exp_time.value(),
            relative=True,
            snaked=True,
        )

    @SafeSlot(popup_error=True)
    def abort(self):
        """Abort the running scan (whole queue, like BEC's stop button)."""
        self.queue.request_scan_abortion()
        self.status.setText("aborted")

    # -- theme -------------------------------------------------------------------------------
    def apply_theme(self, theme: str):
        accent = get_accent_colors()
        self.banner.setStyleSheet(
            "QLabel#aareBanner { font-size: 16px; font-weight: 700; border-left: 1px solid; "
            f"border-bottom: 1px solid; {_BANNER_QSS.get(theme, _BANNER_QSS['light'])} }}"
        )
        self.start_button.setStyleSheet(f"color: {accent.success.name()};")
        self.abort_button.setStyleSheet(f"color: {accent.emergency.name()};")

    def cleanup(self):
        self.bec_dispatcher.disconnect_slot(self.on_scan_progress, MessageEndpoints.scan_progress())
        super().cleanup()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    from aare_bec_widgets.bec_widgets.bluebird import apply_bluebird

    app = QApplication(sys.argv)
    apply_bluebird()  # standalone dev loop shows the same theme bec-app runs with
    widget = AareGridScanControl()
    widget.show()
    sys.exit(app.exec())
