#!/bin/bash
# Local BEC dev loop on the Mac: redis + BEC services in tmux, Qt GUI runs native.
# Mirrors AareDAQ/rhel9-gui.sh verbs so the RHEL9 container script can wrap the same commands later.
#
#   ./dev.sh up        start redis + BEC services (tmux session "bec"), load sim device config
#   ./dev.sh gui       bec-app in Bluebird theme (plugin widgets from this repo show up)
#   ./dev.sh gui dark  bec-app stock dark theme
#   ./dev.sh designer  bec-designer with plugin widgets loaded
#   ./dev.sh gen       regenerate RPC client + Designer stubs (after USER_ACCESS / new widget)
#   ./dev.sh down      stop BEC services + redis
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
# One shared venv lives in the sibling bec_widgets checkout (editable core + this plugin).
VENV="$REPO/../bec_widgets/.venv"
# bec-server writes ./data ./logs ./scripts into cwd -> keep that junk out of the repo.
RUN=/tmp/bec_local
mkdir -p "$RUN"
cd "$RUN"

case "${1:-up}" in
    up)
        # Fresh redis every up, as in the container. A redis orphaned by a previous run (it ignores the
        # SIGHUP tmux sends) keeps stale service-status keys that make wait_for_service below pass early.
        redis-cli shutdown nosave 2>/dev/null || true
        "$VENV/bin/bec-server" start --start-redis --no-persistence
        # Same snippet as Dockerfile.rhel9's entrypoint: bec-server start returns before DeviceServer
        # listens, a config request sent that early gets no reply (302 s timeout).
        "$VENV/bin/python" - <<'PY'
from bec_lib.client import BECClient
c = BECClient(); c.start()
try:
    c.wait_for_service("DeviceServer")
    c.config.load_demo_config()
    from pathlib import Path
    from aare_bec_widgets import device_configs
    c.config.add_to_session(str(Path(device_configs.__file__).with_name("demo_sample_camera.yaml")))
    c.config.add_to_session(str(Path(device_configs.__file__).with_name("smargon_omega.yaml")))
finally:
    c.shutdown()  # non-daemon client threads would otherwise keep python alive forever on error
PY
        echo "ready: ./dev.sh gui   |   tmux attach -t bec   (ctrl+b d to detach)"
        ;;
    gui)
        if [ "${2:-}" = dark ]; then exec "$VENV/bin/bec-app"; fi
        exec "$VENV/bin/python" -m aare_bec_widgets.bec_widgets.bluebird
        ;;
    designer) exec "$VENV/bin/bec-designer" ;;
    gen)      exec "$VENV/bin/bw-generate-cli" --target aare_bec_widgets ;;
    down)
        "$VENV/bin/bec-server" stop
        redis-cli shutdown nosave 2>/dev/null || true   # bec-server stop leaves redis behind, see up
        ;;
    *)
        echo "usage: $0 [up|gui|designer|gen|down]" >&2
        exit 1
        ;;
esac
