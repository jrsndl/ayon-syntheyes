"""Wrap SynthEyes launch in the AYON SyPy controller process."""

from __future__ import annotations

from typing import ClassVar

from ayon_applications import LaunchTypes, PreLaunchHook
from ayon_core.lib import get_ayon_launcher_args

from ayon_syntheyes import get_launch_script_path


class SynthEyesPreLaunch(PreLaunchHook):
    """Replace the direct application launch with the bridge."""

    order = 11
    app_groups: ClassVar[set[str]] = {"syntheyes"}
    launch_types: ClassVar[set[str]] = {LaunchTypes.local}

    def execute(self) -> None:
        original_args = list(self.launch_context.launch_args)
        if not original_args:
            raise RuntimeError("SynthEyes launch has no executable.")

        executable = original_args.pop(0)
        workfile = self.data.get("workfile_path")
        if not workfile and self.data.get("start_last_workfile"):
            workfile = self.data.get("last_workfile_path")
        if workfile and workfile not in original_args:
            original_args.append(workfile)

        wrapped = get_ayon_launcher_args(
            "run",
            get_launch_script_path(),
            executable,
            *original_args,
        )
        self.launch_context.launch_args[:] = [wrapped]
