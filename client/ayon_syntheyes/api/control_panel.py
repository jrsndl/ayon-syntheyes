"""Compact companion window for AYON tools in an external-Python host."""

from __future__ import annotations

from functools import partial

from ayon_core.tools.utils import host_tools
from qtpy import QtCore, QtWidgets


class SynthEyesControlPanel(QtWidgets.QWidget):
    """Artist-facing AYON launcher that lives beside SynthEyes."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AYON - SynthEyes")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(260)

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("AYON tools for SynthEyes")
        title.setObjectName("Headline")
        layout.addWidget(title)

        tools = [
            ("Workfiles", host_tools.show_workfiles),
            ("Load", host_tools.show_loader),
            ("Create", partial(host_tools.show_publisher, tab="create")),
            ("Publish", partial(host_tools.show_publisher, tab="publish")),
            ("Manage", host_tools.show_scene_inventory),
        ]
        for label, callback in tools:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, func=callback: func(parent=self)
            )
            layout.addWidget(button)

        layout.addStretch(1)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Hide the panel without ending the SynthEyes bridge."""
        event.ignore()
        self.hide()
