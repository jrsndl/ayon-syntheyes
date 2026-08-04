"""Create publish instances from matching export-preset profiles."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pyblish.api
from ayon_core.lib import filter_profiles
from ayon_core.pipeline import PublishError

from ayon_syntheyes.api import SynthEyesHost
from ayon_syntheyes.api.export import (
    expand_anatomy_path,
    export_directory,
    index_presets,
    product_name,
    workfile_version,
)
from ayon_syntheyes.plugins.create.create_exports import (
    EXPORT_CREATOR_IDENTIFIER,
    preset_attribute_key,
)


class CollectExportPresets(pyblish.api.ContextPlugin):
    """Create one AYON product instance per expected output definition."""

    order = pyblish.api.CollectorOrder - 0.4
    hosts: ClassVar[list[str]] = ["syntheyes"]
    label = "Collect SynthEyes Export Presets"

    export_presets: ClassVar[list[dict]] = []
    preset_profiles: ClassVar[list[dict]] = []

    @classmethod
    def apply_settings(cls, project_settings: dict) -> None:
        settings = project_settings.get("syntheyes", {}).get("publish", {})
        cls.export_presets = settings.get("export_presets", [])
        cls.preset_profiles = settings.get("preset_profiles", [])

    def process(self, context: pyblish.api.Context) -> None:
        host = SynthEyesHost.get_host()
        if host is None:
            raise PublishError("The SynthEyes host is not installed.")

        workfile = host.get_current_workfile()
        if not workfile:
            raise PublishError(
                "Save the SynthEyes workfile before publishing exports."
            )
        try:
            version = workfile_version(workfile)
            presets_by_name = index_presets(self.export_presets)
        except ValueError as exc:
            raise PublishError(str(exc)) from exc

        task_entity = context.data.get("taskEntity") or {}
        task_name = task_entity.get("name") or context.data.get("task")
        task_type = (
            task_entity.get("taskType") or context.data.get("taskType")
        )
        if not task_name:
            raise PublishError(
                "The current AYON context does not contain a task name."
            )
        profile = filter_profiles(
            self.preset_profiles,
            {
                "task_types": task_type,
                "task_names": task_name,
            },
            keys_order=["task_names", "task_types"],
        )
        if not profile:
            self.log.info(
                "No SynthEyes export profile matches task '%s' (%s).",
                task_name,
                task_type,
            )
            return

        configured_names = list(
            dict.fromkeys(profile.get("export_presets", []))
        )
        enabled_names = self._consume_export_controllers(
            context, configured_names
        )
        if enabled_names is None:
            self.log.info(
                "No SynthEyes Exports instance exists for the current task."
            )
            return
        if not enabled_names:
            self.log.info("All SynthEyes export presets are disabled.")
            return

        anatomy = context.data["anatomy"]
        project_entity = context.data["projectEntity"]
        folder_entity = context.data["folderEntity"]
        used_product_names: set[str] = set()
        for configured_name in enabled_names:
            preset = presets_by_name.get(configured_name.lower())
            if preset is None:
                raise PublishError(
                    f"Export profile references unknown preset "
                    f"'{configured_name}'."
                )
            try:
                preset_path = expand_anatomy_path(
                    preset["preset_path"],
                    anatomy,
                    project_entity,
                    folder_entity,
                    task_entity,
                )
            except ValueError as exc:
                raise PublishError(str(exc)) from exc
            if not Path(preset_path).is_file():
                raise PublishError(
                    f"SynthEyes preset file does not exist: {preset_path}"
                )

            output_dir = export_directory(
                workfile,
                task_name,
                version,
                preset["name"],
            )
            for expected in preset.get("expected_products", []):
                product = product_name(
                    preset["name"], expected, used_product_names
                )
                instance = context.create(product)
                instance.data.update(
                    {
                        "name": product,
                        "label": product,
                        "family": expected["product_type"],
                        "families": ["syntheyes.export"],
                        "productName": product,
                        "productBaseType": expected["product_base_type"],
                        "productType": expected["product_type"],
                        "publish": True,
                        "syntheyesExportPreset": {
                            "name": preset["name"],
                            "syntheyes_exporter": preset[
                                "syntheyes_exporter"
                            ],
                            "preset_path": preset_path,
                            "output_directory": str(output_dir),
                        },
                        "syntheyesExpectedProduct": dict(expected),
                        "workfileVersion": version,
                    }
                )

    def _consume_export_controllers(
        self,
        context: pyblish.api.Context,
        configured_names: list[str],
    ) -> list[str] | None:
        """Remove controller instances and return their enabled presets."""
        controllers = [
            instance
            for instance in list(context)
            if instance.data.get("creator_identifier")
            == EXPORT_CREATOR_IDENTIFIER
        ]
        if not controllers:
            return None

        enabled: set[str] = set()
        for instance in controllers:
            context.remove(instance)
            if not instance.data.get("publish", True):
                continue
            attributes = instance.data.get("creator_attributes") or {}
            stored_names = instance.data.get("syntheyesExportPresetNames")
            allowed_names = set(stored_names or configured_names)
            for name in configured_names:
                if name not in allowed_names:
                    continue
                if attributes.get(preset_attribute_key(name), True):
                    enabled.add(name.lower())

        return [
            name for name in configured_names if name.lower() in enabled
        ]
