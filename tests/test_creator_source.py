from pathlib import Path


def test_creator_instances_are_persistent_and_follow_workfile_version():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "api"
        / "creator.py"
    ).read_text(encoding="utf-8")

    assert 'instance_data["active"] = True' in source
    assert 'instance_data["followWorkfileVersion"] = True' in source
    assert 'instance_data["productBaseType"] = self.product_base_type' in source


def test_review_creator_delegates_to_persistent_base_create():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "create"
        / "create_review.py"
    ).read_text(encoding="utf-8")

    assert "def create(self, product_name, instance_data, pre_create_data):" in source
    assert "return super().create(" in source


def test_control_panel_exposes_publisher_create_tab():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "api"
        / "control_panel.py"
    ).read_text(encoding="utf-8")

    assert '("Create", partial(host_tools.show_publisher, tab="create"))' in source


def test_export_creator_exposes_profile_presets_as_switches():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "create"
        / "create_exports.py"
    ).read_text(encoding="utf-8")

    assert "filter_profiles(" in source
    assert "def get_pre_create_attr_defs(self):" in source
    assert "BoolDef(" in source
    assert 'default=True' in source
    assert 'instance_data["creator_attributes"]' in source


def test_export_collector_consumes_only_enabled_creator_presets():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "publish"
        / "collect_export_presets.py"
    ).read_text(encoding="utf-8")

    assert "def _consume_export_controllers(" in source
    assert "context.remove(instance)" in source
    assert "attributes.get(preset_attribute_key(name), True)" in source


def test_render_creator_exposes_per_instance_output_overrides():
    creator_source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "create"
        / "create_render.py"
    ).read_text(encoding="utf-8")
    extractor_source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "publish"
        / "extract_processed_render.py"
    ).read_text(encoding="utf-8")

    assert 'BoolDef(\n                "reset_filtering_color"' in creator_source
    assert 'EnumDef(\n                "file_extension"' in creator_source
    assert 'instance_data["creator_attributes"]' in creator_source
    assert 'instance.data.get("creator_attributes")' in extractor_source
    assert '"reset_filtering_color": reset_filtering_color' in extractor_source
