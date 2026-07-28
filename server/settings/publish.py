"""Profile-driven SynthEyes export settings."""

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
)


class ExpectedProductModel(BaseSettingsModel):
    """File matching and AYON product typing for one exporter output."""

    extension: str = SettingsField(
        "",
        title="Extension",
        description="Extension without a leading dot, for example 'nk'.",
        pattern=r"^[A-Za-z0-9]+$",
    )
    file_name_includes: str = SettingsField(
        "",
        title="File name includes",
        description="Optional case-insensitive substring filter.",
    )
    product_base_type: str = SettingsField(
        "workfile",
        title="Product base type",
    )
    product_type: str = SettingsField(
        "workfile",
        title="Product type",
    )


class ExportPresetModel(BaseSettingsModel):
    """One native SynthEyes exporter and its expected AYON outputs."""

    _layout = "expanded"

    name: str = SettingsField(
        "",
        title="Name",
        description="Unique filename-safe preset name.",
        pattern=r"^[A-Za-z0-9_]+$",
    )
    syntheyes_exporter: str = SettingsField(
        "",
        title="SynthEyes exporter",
        description=(
            "Sizzle exporter filename, for example 'Nuke/nuke.szl', "
            "'alembic.szl', 'filmbox.szl', or 'blender25.szl'."
        ),
    )
    preset_path: str = SettingsField(
        "",
        title="Path to SynthEyes preset file",
        description=(
            "Workflow Preset JSON containing exactly one Multi-Export stage. "
            "AYON anatomy tokens such as {root[work]} and {project[name]} "
            "are supported."
        ),
    )
    expected_products: list[ExpectedProductModel] = SettingsField(
        default_factory=list,
        title="Expected products",
    )


class ExportProfileModel(BaseSettingsModel):
    """Select export presets for a task context."""

    _layout = "expanded"

    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum,
    )
    task_names: list[str] = SettingsField(
        default_factory=list,
        title="Task names",
    )
    export_presets: list[str] = SettingsField(
        default_factory=list,
        title="Export presets",
        description="Names declared in the Export Presets list.",
    )


class PublishSettings(BaseSettingsModel):
    """All profile-driven SynthEyes publishing settings."""

    export_presets: list[ExportPresetModel] = SettingsField(
        default_factory=list,
        title="Export presets",
    )
    preset_profiles: list[ExportProfileModel] = SettingsField(
        default_factory=list,
        title="Preset profiles",
    )


DEFAULT_PUBLISH_SETTINGS = {
    "export_presets": [],
    "preset_profiles": [],
}
