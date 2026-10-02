def main():  # pragma: no cover
    from qtpy import PYSIDE6

    if not PYSIDE6:
        print("PYSIDE6 is not available in the environment. Cannot patch designer.")
        return
    from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection

    from aare_bec_widgets.bec_widgets.widgets.grid_scan_control.aare_grid_scan_control_plugin import (
        AareGridScanControlPlugin,
    )

    QPyDesignerCustomWidgetCollection.addCustomWidget(AareGridScanControlPlugin())


if __name__ == "__main__":  # pragma: no cover
    main()
