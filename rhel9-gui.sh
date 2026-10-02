#!/bin/bash
# Rocky Linux 9 (RHEL9-compatible) container running redis + BEC server + the BEC GUI with this
# plugin loaded, visible in the browser at http://localhost:6081/vnc.html (noVNC).
# Same verbs as dev.sh, so the Mac-native and RHEL9 loops stay interchangeable.
#
#   ./rhel9-gui.sh            build image if missing, (re)start container (starts BEC inside), print URL
#   ./rhel9-gui.sh gui        bec-app in Bluebird theme (watch the browser tab)
#   ./rhel9-gui.sh gui dark   bec-app stock dark theme
#   ./rhel9-gui.sh designer   bec-designer with plugin widgets loaded
#   ./rhel9-gui.sh bec        attach to the BEC server tmux session inside the container (ctrl+b d to detach)
#   ./rhel9-gui.sh shell      bash inside the container
#   ./rhel9-gui.sh down       remove the container (venv + config volumes survive)
#   ./rhel9-gui.sh --build    force image rebuild
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
# bec_widgets core is mounted editable so core patches are testable on RHEL9 too (same as dev.sh's shared venv).
CORE="$(cd "$REPO/../bec_widgets" && pwd)"
IMG=aare-bec-widgets-rhel9
CTR=aare-bec-widgets-rhel9
# 6081: AareDAQ's rhel9 container already publishes 6080 on this Mac.
PORT=6081

# amd64 everywhere (Rosetta on Apple Silicon): see Dockerfile.rhel9 header.
PLATFORM=linux/amd64

build() {
    # stdin build = empty context: the repos (.venv, .git, data) are never tarred to the daemon
    docker build --platform "$PLATFORM" -t "$IMG" - < "$REPO/Dockerfile.rhel9"
}

case "${1:-up}" in
    --build|build)
        build
        docker rm -f "$CTR" 2>/dev/null || true
        exec "$0" up
        ;;
    up)
        docker image inspect "$IMG" >/dev/null 2>&1 || build
        if [ -z "$(docker ps -q -f "name=^${CTR}$")" ]; then
            docker rm "$CTR" 2>/dev/null || true
            # config volume: QSettings (theme, layouts) live in /root/.config — without it every recreate resets the GUI
            docker run -d --platform "$PLATFORM" --name "$CTR" \
                -v "$REPO:/workspace" \
                -v "$CORE:/bec_widgets" \
                -v aare-bec-widgets-rhel9-venv:/opt/venv \
                -v aare-bec-widgets-rhel9-config:/root/.config \
                -p 127.0.0.1:$PORT:6080 \
                "$IMG" >/dev/null
        fi
        echo "GUI display:  http://localhost:$PORT/vnc.html?autoconnect=1&resize=scale"
        echo "  (1:1 view:  http://localhost:$PORT/vnc.html?autoconnect=1&resize=remote)"
        echo "First run installs deps from PyPI, then starts redis + BEC — progress: docker logs -f $CTR"
        echo "Launch GUI:   $0 gui      Shell: $0 shell      BEC tmux: $0 bec"
        ;;
    gui|designer)
        # replace any GUI already running instead of stacking a second one
        docker exec "$CTR" pkill -f 'bluebird|bec-app|bec-designer' 2>/dev/null || true
        # self-heal: the venv volume outlives dependency bumps in pyproject — editable reinstall is a ~1s no-op when current
        docker exec "$CTR" uv pip install -q -e /bec_widgets -e '/workspace[dev]' || \
            echo ">>> dep refresh failed (offline?) — trying to launch anyway"
        if [ "$1" = designer ]; then exec docker exec -it "$CTR" bec-designer; fi
        if [ "${2:-}" = dark ]; then exec docker exec -it "$CTR" bec-app; fi
        exec docker exec -it "$CTR" python -m aare_bec_widgets.bec_widgets.bluebird
        ;;
    bec)   exec docker exec -it "$CTR" tmux attach -t bec ;;
    shell) exec docker exec -it "$CTR" bash ;;
    down)  docker rm -f "$CTR" ;;
    *)
        echo "usage: $0 [up|gui [dark]|designer|bec|shell|down|--build]" >&2
        exit 1
        ;;
esac
