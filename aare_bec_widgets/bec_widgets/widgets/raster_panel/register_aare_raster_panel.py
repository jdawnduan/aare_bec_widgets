def main():  # pragma: no cover
    from qtpy import PYSIDE6

    if not PYSIDE6:
        print("PYSIDE6 is not available in the environment. Cannot patch designer.")
        return
    from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection

    from aare_bec_widgets.bec_widgets.widgets.raster_panel.aare_raster_panel_plugin import (
        AareRasterPanelPlugin,
    )

    QPyDesignerCustomWidgetCollection.addCustomWidget(AareRasterPanelPlugin())


if __name__ == "__main__":  # pragma: no cover
    main()
