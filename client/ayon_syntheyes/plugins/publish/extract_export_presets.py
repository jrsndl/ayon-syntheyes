"""Run native Multi-Export stages and collect their output files."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import ClassVar

import pyblish.api
from ayon_core.pipeline import PublishError

from ayon_syntheyes.api import SynthEyesHost
from ayon_syntheyes.api.export import matching_files


class ExtractExportPresets(pyblish.api.ContextPlugin):
    """Export every configured native preset once, then fill representations."""

    order = pyblish.api.ExtractorOrder - 0.1
    hosts: ClassVar[list[str]] = ["syntheyes"]
    label = "Export SynthEyes Products"

    def process(self, context: pyblish.api.Context) -> None:
        host = SynthEyesHost.get_host()
        if host is None:
            raise PublishError("The SynthEyes host is not installed.")

        instances_by_preset = defaultdict(list)
        for instance in context:
            preset = instance.data.get("syntheyesExportPreset")
            if preset and instance.data.get("publish", True):
                instances_by_preset[preset["name"]].append(instance)

        for instances in instances_by_preset.values():
            preset = instances[0].data["syntheyesExportPreset"]
            output_directory = Path(preset["output_directory"])
            self.log.info(
                "Running SynthEyes exporter '%s' into '%s'.",
                preset["syntheyes_exporter"],
                output_directory,
            )
            host.export_with_preset(
                preset["syntheyes_exporter"],
                preset["preset_path"],
                str(output_directory),
            )
            for instance in instances:
                self._collect_instance(instance, output_directory)

    def _collect_instance(
        self,
        instance: pyblish.api.Instance,
        output_directory: Path,
    ) -> None:
        expected = instance.data["syntheyesExpectedProduct"]
        files = matching_files(
            output_directory,
            expected["extension"],
            expected.get("file_name_includes", ""),
        )
        if not files:
            includes = expected.get("file_name_includes") or "<any>"
            raise PublishError(
                f"No files matched extension '.{expected['extension']}' "
                f"and filename filter '{includes}' in "
                f"'{output_directory}'."
            )

        relative_files = [
            str(path.relative_to(output_directory)).replace("\\", "/")
            for path in files
        ]
        representation_files = (
            relative_files[0] if len(relative_files) == 1 else relative_files
        )
        extension = expected["extension"].lower().lstrip(".")
        instance.data["representations"] = [
            {
                "name": extension,
                "ext": extension,
                "files": representation_files,
                "stagingDir": str(output_directory),
            }
        ]
