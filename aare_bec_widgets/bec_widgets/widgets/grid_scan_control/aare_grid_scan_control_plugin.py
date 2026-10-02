# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from bec_widgets.utils.bec_designer import designer_material_icon
from qtpy.QtDesigner import QDesignerCustomWidgetInterface
from qtpy.QtWidgets import QWidget

from aare_bec_widgets.bec_widgets.widgets.grid_scan_control.grid_scan_control import (
    AareGridScanControl,
)

DOM_XML = """
<ui language='c++'>
    <widget class='AareGridScanControl' name='aare_grid_scan_control'>
    </widget>
</ui>
"""


class AareGridScanControlPlugin(QDesignerCustomWidgetInterface):  # pragma: no cover
    def __init__(self):
        super().__init__()
        self._form_editor = None

    def createWidget(self, parent):
        if parent is None:
            return QWidget()
        t = AareGridScanControl(parent)
        return t

    def domXml(self):
        return DOM_XML

    def group(self):
        return ""

    def icon(self):
        return designer_material_icon(AareGridScanControl.ICON_NAME)

    def includeFile(self):
        return "aare_grid_scan_control"

    def initialize(self, form_editor):
        self._form_editor = form_editor

    def isContainer(self):
        return False

    def isInitialized(self):
        return self._form_editor is not None

    def name(self):
        return "AareGridScanControl"

    def toolTip(self):
        return "Raster (grid) scan control: two motors, element pitch, image time, grid elements -> scans.grid_scan."

    def whatsThis(self):
        return self.toolTip()
