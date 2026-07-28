import pytest

from ayon_syntheyes.api.clip import (
    DEPTH_VALUES,
    OUTPUT_DEPTH_VALUES,
    entity_fps,
)


def test_fps_prefers_task_over_folder_and_version():
    context = {
        "task": {"attrib": {"fps": 25}},
        "folder": {"attrib": {"fps": 24}},
        "version": {"attrib": {"fps": 23.976}},
    }
    assert entity_fps(context) == 25.0


def test_fps_falls_back_to_folder():
    context = {"task": {"attrib": {}}, "folder": {"attrib": {"fps": 24}}}
    assert entity_fps(context) == 24.0


def test_fps_is_required():
    with pytest.raises(RuntimeError, match="does not define a valid FPS"):
        entity_fps({})


def test_depth_mappings_match_sizzle_api():
    assert DEPTH_VALUES["Half"] == 2
    assert OUTPUT_DEPTH_VALUES["Half"] == 2
    assert OUTPUT_DEPTH_VALUES["Follow process depth"] == -1
