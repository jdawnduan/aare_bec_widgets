"""Camera view + raster control in one panel, like AareDAQ's main window (sample camera + data collection).

Why: the drawn grid lives on the camera image and the scan parameters live in the control; wiring the
two with a direct Qt signal inside one widget needs no registry lookup. Side by side (camera left,
numbers right) like AareDAQ's main window, so the grid and its parameters are visible at once. The ROI
is BEC's RectangularROI, so the user gets BEC's move/resize handles instead of AareDAQ's right-drag gesture.
"""

from __future__ import annotations

from bec_lib.logger import bec_logger
from bec_widgets.utils.bec_widget import BECWidget
from bec_widgets.utils.error_popups import SafeProperty, SafeSlot
from bec_widgets.widgets.plots.image.image import Image
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QSplitter, QVBoxLayout, QWidget

from aare_bec_widgets.bec_widgets.widgets.grid_scan_control.grid_scan_control import (
    AareGridScanControl,
)

logger = bec_logger.logger


class AareRasterPanel(BECWidget, QWidget):
    """Left: `Image` on `<camera_device>.preview` with a rect ROI. Right: AareGridScanControl fed by that ROI."""

    PLUGIN = True
    ICON_NAME = "photo_camera"
    USER_ACCESS = ["camera_device", "camera_device.setter", "attach", "detach"]

    def __init__(
        self,
        parent=None,
        client=None,
        config=None,
        gui_id=None,
        camera_device: str = "samcam",
        **kwargs,
    ):
        super().__init__(parent=parent, client=client, config=config, gui_id=gui_id, **kwargs)
        self.get_bec_shortcuts()
        self._camera_device = ""
        self._calibration = (
            1.0,
            1.0,
            0.0,
            0.0,
        )  # um_per_px_x, um_per_px_y, beam_cx, beam_cy; raw pixels until a device is set
        self._edges: tuple[float, float, float, float] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(self.splitter)

        self.camera = Image(parent=self, client=self.client, popups=False)
        # Camera convention: x = column, y = row, row 0 at the top. pyqtgraph would otherwise draw array
        # axis 0 along x (portrait) with y up. Image ignores PreviewSignal's transpose metadata, so set it here;
        # ROI edges then arrive as (col, row), matching the device's beam_center_* signals.
        self.camera.transpose = True
        self.camera.invert_y = True
        self.camera.lock_aspect_ratio = True
        self.control = AareGridScanControl(parent=self, client=self.client)
        self.splitter.addWidget(self.camera)
        self.splitter.addWidget(self.control)
        # camera takes the slack; the numbers column keeps AareDAQ's narrow panel width
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.control.setMinimumWidth(380)
        self.splitter.setSizes([700, 420])

        self.roi = self.camera.add_roi("rect", name="grid", pos=(220, 180), size=(200, 120))
        self.roi.edgesChanged.connect(self._on_roi_changed)
        # edgesChanged only fires on change: seed from the initial rectangle so the numbers match it at once
        pos, size = self.roi.pos(), self.roi.size()
        self._edges = (pos.x(), pos.y(), pos.x() + size.x(), pos.y() + size.y())

        self.camera_device = camera_device

    @SafeProperty(str)
    def camera_device(self) -> str:
        """Device whose `preview` signal is shown; its um_per_px_* / beam_center_* signals calibrate the ROI."""
        return self._camera_device

    @camera_device.setter
    def camera_device(self, name: str):
        self._camera_device = name
        if not name:
            return
        try:
            self.camera.image(device=name, signal="preview")
            cam = self.dev[name]
            self._calibration = (
                float(cam.um_per_px_x.get()),
                float(cam.um_per_px_y.get()),
                float(cam.beam_center_x.get()),
                float(cam.beam_center_y.get()),
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 - device not in session yet: show nothing, keep pixel units
            logger.warning(
                f"AareRasterPanel: camera {name!r} not usable ({exc}); ROI stays in pixels"
            )
        if self._edges:
            self._on_roi_changed(*self._edges)

    @SafeSlot(float, float, float, float)
    def _on_roi_changed(self, x0: float, y0: float, x1: float, y1: float):
        self._edges = (x0, y0, x1, y1)
        self.control.set_grid_from_pixels(x0, y0, x1, y1, *self._calibration)

    def cleanup(self):
        self.camera.cleanup()
        self.control.cleanup()
        super().cleanup()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    from aare_bec_widgets.bec_widgets.bluebird import apply_bluebird

    app = QApplication(sys.argv)
    apply_bluebird()
    widget = AareRasterPanel()
    widget.resize(1120, 600)
    widget.show()
    sys.exit(app.exec())
