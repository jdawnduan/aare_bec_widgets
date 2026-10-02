"""Launch bec-app with the AareDAQ Bluebird color scheme.

Why: bec-app's main() hardcodes apply_theme("dark") and has no theme flag, while
bec_qthemes.apply_theme already accepts a path to a theme XML. Swapping the name main()
looks up at call time is shorter than copying main(). Colors live in bluebird.xml.
"""

from pathlib import Path

import bec_qthemes

from bec_widgets.applications import main_app

BLUEBIRD_XML = Path(__file__).with_name("bluebird.xml")


def apply_bluebird(*_args) -> None:
    """Apply Bluebird to the running QApplication (signature-compatible with apply_theme)."""
    bec_qthemes.apply_theme(BLUEBIRD_XML)


def main() -> None:
    # ponytail: module-attr swap; upstream a --theme flag on bec-app if more themes appear
    main_app.apply_theme = apply_bluebird
    main_app.main()


if __name__ == "__main__":
    main()
