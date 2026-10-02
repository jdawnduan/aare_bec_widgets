from qtpy.QtWidgets import QWidget

from bec_widgets.utils.bec_widget import BECWidget



class AareDemoWidget(BECWidget, QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = AareDemoWidget()
    widget.show()
    sys.exit(app.exec())