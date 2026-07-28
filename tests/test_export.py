"""Tests for dependency-free export preset helpers."""

import pytest

from ayon_syntheyes.api.export import (
    expand_anatomy_path,
    export_directory,
    index_presets,
    matching_files,
    product_name,
    validate_preset_name,
    workfile_version,
)


class _Anatomy:
    roots = {"work": "W:/projects"}


def test_validate_preset_name():
    assert validate_preset_name("Nuke_full_2") == "Nuke_full_2"
    with pytest.raises(ValueError, match="Only a-z"):
        validate_preset_name("Nuke full")


def test_workfile_version_uses_last_version_token():
    assert workfile_version("shot_v002_matchmove_v017.sni") == 17
    with pytest.raises(ValueError, match="version token"):
        workfile_version("shot_matchmove.sni")


def test_export_directory_follows_task_version_preset(tmp_path):
    workfile = tmp_path / "shot_v003.sni"
    assert export_directory(
        str(workfile), "matchmove", 3, "nuke"
    ) == tmp_path / "matchmove" / "v003" / "nuke"


def test_expand_anatomy_path():
    value = expand_anatomy_path(
        "{root[work]}/{project[name]}/{task[name]}/nuke.json",
        _Anatomy(),
        {"name": "demo"},
        {"name": "shot010"},
        {"name": "matchmove"},
    )
    assert value == "W:/projects/demo/matchmove/nuke.json"


def test_matching_files_is_recursive_and_case_insensitive(tmp_path):
    nested = tmp_path / "maps"
    nested.mkdir()
    wanted = nested / "shot_UNDISTORT.EXT.exr"
    wanted.write_text("test", encoding="utf-8")
    (nested / "shot_redistort.exr").write_text("test", encoding="utf-8")
    assert matching_files(tmp_path, ".EXR", "undistort") == [wanted]


def test_product_names_are_unique():
    used = set()
    expected = {"extension": "exr", "file_name_includes": "ST Map"}
    assert product_name("nuke", expected, used) == "nuke_ST_Map"
    assert product_name("nuke", expected, used) == "nuke_ST_Map_2"


def test_index_presets_rejects_case_insensitive_duplicates():
    with pytest.raises(ValueError, match="Duplicate"):
        index_presets([{"name": "Nuke"}, {"name": "nuke"}])
