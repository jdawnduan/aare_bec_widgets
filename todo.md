# TODO (local dev env, 2026-10-02)

- Skipped: git clone of `bec` / `ophyd_devices`. Add when you need an unreleased core change
  (today: PyPI bec_lib/bec_server 3.173.1, ophyd_devices 1.47.1; bec_widgets 3.37.3 editable from `../bec_widgets`).
- Done 2026-10-02: RHEL9 container = `Dockerfile.rhel9` + `rhel9-gui.sh` (ported from AareDAQ, + redis/tmux,
  BEC starts inside the container, noVNC on http://localhost:6081 because aaredaq-rhel9 holds 6080).
  Same verbs as `dev.sh`: up / gui [dark] / designer / bec / shell / down / --build.
- Bluebird: View menu "Light Theme" / dark-mode toggle falls back to stock light. Fix = `--theme` flag on
  `bec-app` upstream, not done.
- Found 2026-10-02 (not fixed, out of scope): FileWriter logs
  `Error loading storage copy plugin plugin_storage_copy: module 'aare_bec_widgets.file_writer.storage_copy' has no attribute 'plugin_storage_copy'`
  -> copier template registers the entry point in pyproject but ships the function commented out. Harmless until
  `bec.beamline_storage_copy()` is used; either implement it or drop the `bec.file_writer.storage_copy` entry point.
- Done 2026-10-02: `AareGridScanControl` (widgets/grid_scan_control) = AareDAQ "Raster data collection" panel on
  BEC `grid_scan`; `AareRasterPanel` (widgets/raster_panel) = camera left (BEC `Image` on `samcam.preview` + rect ROI)
  | raster numbers right (QSplitter, AareDAQ main-window layout); ROI edges -> n_x/n_y + grid centre via the camera's um_per_px_* / beam_center_* signals.
  `devices/sample_camera.py` `AareSampleCamera` streams a synthetic blob at 5 fps (device_configs/demo_sample_camera.yaml,
  added after the demo config by dev.sh / the container entrypoint).
  - TODO(url): production stream. zmq (AareDAQ camera_thread.py format) and Axis MJPEG readers are written but
    untested: no camera reachable from the dev box. Set deviceConfig.url + calibrate um_per_px/beam_center per zoom.
  - Skipped: metric combo, transparency slider, evaluated-grid table/heatmap, X-ray centering. Results back onto the
    camera = next step (scan data -> Heatmap/overlay).
  - ROI pixel axes vs motor sense only checked on the synthetic image; verify sign of um_per_px_y on the beamline.
- `aare_demo_widget` is still the empty copier stub; delete it once a second real widget lands (copier may re-add it
  on `copier update` since it is listed in .copier-answers.yml).
