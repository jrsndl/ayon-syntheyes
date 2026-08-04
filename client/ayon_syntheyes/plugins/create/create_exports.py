"""Create a profile-driven SynthEyes export controller."""

from __future__ import annotations

from ayon_core.lib import BoolDef, filter_profiles

from ayon_syntheyes.api.creator import SynthEyesCreator


EXPORT_CREATOR_IDENTIFIER = "io.ayon.creators.syntheyes.exports"
PRESET_ATTRIBUTE_PREFIX = "export_preset__"


def preset_attribute_key(preset_name: str) -> str:
    """Return the creator-attribute key for an export preset."""
    return f"{PRESET_ATTRIBUTE_PREFIX}{preset_name}"


class CreateExports(SynthEyesCreator):
    """Select native export presets for the current task profile."""

    identifier = EXPORT_CREATOR_IDENTIFIER
    label = "Exports"
    product_base_type = "export"
    product_type = "syntheyesExports"
    icon = "upload"
    enabled = True
    default_variants = ["Main"]

    def _profile_preset_names(self) -> list[str]:
        publish_settings = (
            self.project_settings.get("syntheyes", {}).get("publish", {})
        )
        task_entity = self.create_context.get_current_task_entity() or {}
        profile = filter_profiles(
            publish_settings.get("preset_profiles", []),
            {
                "task_types": task_entity.get("taskType"),
                "task_names": task_entity.get("name"),
            },
            keys_order=["task_names", "task_types"],
        )
        if not profile:
            return []
        return list(dict.fromkeys(profile.get("export_presets", [])))

    def _preset_attr_defs(self):
        return [
            BoolDef(
                preset_attribute_key(preset_name),
                label=preset_name,
                tooltip=f"Run the {preset_name} SynthEyes export preset.",
                default=True,
            )
            for preset_name in self._profile_preset_names()
        ]

    def get_pre_create_attr_defs(self):
        """Show enabled-by-default switches for the matching profile."""
        return self._preset_attr_defs()

    def get_attr_defs_for_instance(self, instance):
        """Keep preset switches editable after the instance is created."""
        return self._preset_attr_defs()

    def create(self, product_name, instance_data, pre_create_data):
        """Persist the export selection for expansion during publishing."""
        preset_names = self._profile_preset_names()
        creator_attributes = {
            preset_attribute_key(name): pre_create_data.get(
                preset_attribute_key(name), True
            )
            for name in preset_names
        }
        instance_data = dict(instance_data)
        instance_data["creator_attributes"] = creator_attributes
        instance_data["syntheyesExportPresetNames"] = preset_names
        return super().create(
            product_name,
            instance_data,
            pre_create_data,
        )
