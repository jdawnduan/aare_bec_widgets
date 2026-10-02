# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from bec_widgets.utils.bec_designer import designer_material_icon
from qtpy.QtDesigner import QDesignerCustomWidgetInterface
from qtpy.QtWidgets import QWidget

from aare_bec_widgets.bec_widgets.widgets.raster_panel.raster_panel import AareRasterPanel

DOM_XML = """
<ui language='c++'>
    <widget class='AareRasterPanel' name='aare_raster_panel'>
    </widget>
</ui>
"""


class AareRasterPanelPlugin(QDesignerCustomWidgetInterface):  # pragma: no cover
    def __init__(self):
        super().__init__()
        self._form_editor = None

    def createWidget(self, parent):
        if parent is None:
            return QWidget()
        t = AareRasterPanel(parent)
        return t

    def domXml(self):
        return DOM_XML

    def group(self):
        return ""

    def icon(self):
        return designer_material_icon(AareRasterPanel.ICON_NAME)

    def includeFile(self):
        return "aare_raster_panel"

    def initialize(self, form_editor):
        self._form_editor = form_editor

    def isContainer(self):
        return False

    def isInitialized(self):
        return self._form_editor is not None

    def name(self):
        return "AareRasterPanel"

    def toolTip(self):
        return "Tab 'Camera': `Image` on `<camera_device>.preview` with a rect ROI; tab 'Raster': AareGridScanControl."

    def whatsThis(self):
        return self.toolTip()
