"""Client addon definition."""

from __future__ import annotations

import os
from typing import Any

from ayon_core.addon import AYONAddon, IHostAddon

from . import SYNTH_EYES_HOST_DIR
from .version import __version__


class SynthEyesAddon(AYONAddon, IHostAddon):
    """Expose SynthEyes as an AYON host."""

    name = "syntheyes"
    host_name = "syntheyes"
    version = __version__

    def initialize(self, settings: dict[str, Any]) -> None:
        host_settings = settings.get(self.name, {})
        self.connect_timeout = float(host_settings.get("connect_timeout", 60))
        self.sy_py_directory = host_settings.get("sy_py_directory", "")
        self.enabled = True

    def add_implementation_envs(self, env: dict, _app: Any) -> None:
        env["AYON_SYNTHEYES_CONNECT_TIMEOUT"] = str(self.connect_timeout)
        if self.sy_py_directory:
            env["AYON_SYNTHEYES_SYPY_DIR"] = self.sy_py_directory

    def get_launch_hook_paths(self) -> list[str]:
        return [os.path.join(SYNTH_EYES_HOST_DIR, "hooks")]

    def get_workfile_extensions(self) -> list[str]:
        return [".sni"]
