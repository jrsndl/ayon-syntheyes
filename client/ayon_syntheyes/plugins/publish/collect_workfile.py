"""Collect the open SynthEyes scene as the current workfile."""

from typing import ClassVar

import pyblish.api

from ayon_syntheyes.api import SynthEyesHost


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Expose the current .sni path to AYON's generic publish pipeline."""

    order = pyblish.api.CollectorOrder - 0.5
    hosts: ClassVar[list[str]] = ["syntheyes"]
    label = "Collect SynthEyes Workfile"

    def process(self, context: pyblish.api.Context) -> None:
        host = SynthEyesHost.get_host()
        if host is None:
            raise RuntimeError("The SynthEyes host is not installed.")
        context.data["currentFile"] = host.get_current_workfile()
