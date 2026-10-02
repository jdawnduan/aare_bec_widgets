"""Sample camera streamed into BEC as a 2D PreviewSignal.

Why: BEC shows cameras through redis (`device_preview`), not by pulling a video URL inside the GUI
the way AareDAQ does (gui/threads/camera_thread.py, axis_video_thread.py). This device is that
bridge: the device server runs it, the Image widget subscribes to `samcam.preview`.

Demo: no `url` -> synthetic drifting blob, so the stream visibly moves.
Production: set `url` in the device config (device_configs/demo_sample_camera.yaml). The two
formats AareDAQ consumes are implemented below but UNTESTED here (no camera reachable from the
dev box). TODO(url): verify both readers on the beamline network before relying on them.
"""

from __future__ import annotations

import io
import json
import threading
import time
from collections.abc import Iterator

import numpy as np
from bec_lib.logger import bec_logger
from ophyd import Component as Cpt
from ophyd import Kind
from ophyd_devices.interfaces.base_classes.psi_device_base import PSIDeviceBase
from ophyd_devices.sim.sim_signals import SetableSignal
from ophyd_devices.utils.bec_signals import PreviewSignal

logger = bec_logger.logger


class AareSampleCamera(PSIDeviceBase):
    """Publishes grayscale frames at `fps` from `url` (zmq/MJPEG) or a synthetic source."""

    SHAPE = (480, 640)

    preview = Cpt(PreviewSignal, name="preview", ndim=2)
    # Pixel calibration the GUI reads to turn a drawn ROI into motor distances (AareDAQ keeps this in
    # DiffractionGeometry). Units: µm per image pixel along the plot x / y axis; negative = flipped
    # motor sense. Zoom-dependent in production -> set per zoom level later.
    um_per_px_x = Cpt(SetableSignal, name="um_per_px_x", value=1.0, kind=Kind.config)
    um_per_px_y = Cpt(SetableSignal, name="um_per_px_y", value=-1.0, kind=Kind.config)
    beam_center_x = Cpt(SetableSignal, name="beam_center_x", value=320.0, kind=Kind.config)
    beam_center_y = Cpt(SetableSignal, name="beam_center_y", value=240.0, kind=Kind.config)

    def __init__(
        self, prefix: str = "", *, name: str, url: str | None = None, fps: float = 5.0, **kwargs
    ):
        self.url = url or None
        self.fps = float(fps)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        super().__init__(prefix, name=name, **kwargs)

    # device server calls this after it subscribed to our BEC signals -> frames are not dropped
    def on_connected(self) -> None:
        self._thread = threading.Thread(
            target=self._stream, name=f"{self.name}-stream", daemon=True
        )
        self._thread.start()

    def on_destroy(self) -> None:
        self._stop.set()

    def _stream(self) -> None:
        period = 1.0 / self.fps
        frames = self._frames()
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                self.preview.put(next(frames))
            except Exception:  # noqa: BLE001 - keep the stream alive, log and retry the source
                logger.exception(f"{self.name}: frame source {self.url!r} failed, retrying in 1 s")
                self._stop.wait(1.0)
                frames = self._frames()
                continue
            self._stop.wait(max(0.0, period - (time.monotonic() - t0)))

    def _frames(self) -> Iterator[np.ndarray]:
        if not self.url:
            return self._synthetic_frames()
        if self.url.startswith("tcp://"):
            return self._zmq_frames()
        if self.url.startswith("http"):
            return self._mjpeg_frames()
        raise ValueError(f"{self.name}: unsupported url {self.url!r} (tcp:// zmq or http MJPEG)")

    def _synthetic_frames(self) -> Iterator[np.ndarray]:
        h, w = self.SHAPE
        yy, xx = np.mgrid[0:h, 0:w]
        rng = np.random.default_rng(0)
        k = 0
        while True:
            cx, cy = w / 2 + 80 * np.cos(k / 20), h / 2 + 60 * np.sin(k / 20)
            blob = 200 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 30**2))
            frame = (blob + rng.normal(20, 5, (h, w))).clip(0, 255).astype(np.uint8)
            frame[:20, :120] = (
                255  # top-left bar: makes display orientation checkable (row 0 = top)
            )
            yield frame
            k += 1

    def _mjpeg_frames(self) -> Iterator[np.ndarray]:
        # Axis MJPEG: same JPEG SOI/EOI scan as AareDAQ axis_video_thread.py; PIL instead of cv2 (not in venv).
        import requests
        from PIL import Image

        buf = b""
        with requests.get(self.url, stream=True, timeout=10) as resp:
            for chunk in resp.iter_content(64 * 1024):
                buf += chunk
                while True:
                    start = buf.find(b"\xff\xd8")
                    end = buf.find(b"\xff\xd9", start) if start >= 0 else -1
                    if end < 0:
                        break
                    jpeg, buf = buf[start : end + 2], buf[end + 2 :]
                    yield np.asarray(Image.open(io.BytesIO(jpeg)).convert("L"))

    def _zmq_frames(self) -> Iterator[np.ndarray]:
        # AareDAQ sample camera: multipart [json header, data]; encoding "jpeg", or raw with "shape"
        # (gui/threads/camera_thread.py). Raw Bayer is shown as-is (grey), no demosaic.
        import zmq
        from PIL import Image

        sock = zmq.Context.instance().socket(zmq.SUB)
        sock.connect(self.url)
        sock.setsockopt(zmq.SUBSCRIBE, b"")
        while True:
            parts = sock.recv_multipart()
            header = next((json.loads(p) for p in parts[:-1] if p[:1] == b"{"), {})
            data = parts[-1]
            if header.get("encoding", "").lower() == "jpeg":
                yield np.asarray(Image.open(io.BytesIO(data)).convert("L"))
            elif "shape" in header:
                h, w = header["shape"][:2]
                yield np.frombuffer(data, np.uint8).reshape(h, w)
            else:
                raise ValueError(f"{self.name}: unsupported zmq frame header {header}")
