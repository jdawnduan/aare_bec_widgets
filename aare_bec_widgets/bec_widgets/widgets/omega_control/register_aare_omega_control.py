def main():  # pragma: no cover
    from qtpy import PYSIDE6

    if not PYSIDE6:
        print("PYSIDE6 is not available in the environment. Cannot patch designer.")
        return
    from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection

    from aare_bec_widgets.bec_widgets.widgets.omega_control.aare_omega_control_plugin import AareOmegaControlPlugin

    QPyDesignerCustomWidgetCollection.addCustomWidget(AareOmegaControlPlugin())


if __name__ == "__main__":  # pragma: no cover
    main()
