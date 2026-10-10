# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from qtpy.QtDesigner import QDesignerCustomWidgetInterface
from qtpy.QtWidgets import QWidget

from bec_widgets.utils.bec_designer import designer_material_icon
from aare_bec_widgets.bec_widgets.widgets.omega_control.omega_control import AareOmegaControl

DOM_XML = """
<ui language='c++'>
    <widget class='AareOmegaControl' name='aare_omega_control'>
    </widget>
</ui>
"""


class AareOmegaControlPlugin(QDesignerCustomWidgetInterface):  # pragma: no cover
    def __init__(self):
        super().__init__()
        self._form_editor = None

    def createWidget(self, parent):
        if parent is None:
            return QWidget()
        t = AareOmegaControl(parent)
        return t

    def domXml(self):
        return DOM_XML

    def group(self):
        return "Aare Device Control"

    def icon(self):
        return designer_material_icon(AareOmegaControl.ICON_NAME)

    def includeFile(self):
        return "aare_omega_control"

    def initialize(self, form_editor):
        self._form_editor = form_editor

    def isContainer(self):
        return False

    def isInitialized(self):
        return self._form_editor is not None

    def name(self):
        return "AareOmegaControl"

    def toolTip(self):
        return "Omega rotation of the SMARGON goniometer: live angle, go-to, stop and preset moves."

    def whatsThis(self):
        return self.toolTip()
