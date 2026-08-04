from pathlib import Path


def test_clip_loader_activates_imported_camera_inside_undo_block():
    """SetActive is valid only between Begin and Accept/Cancel."""
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "load"
        / "load_clip.py"
    ).read_text(encoding="utf-8")

    begin = source.index("host.level.Begin()", source.index("def _add_shot("))
    activate = source.index("host.level.SetActive(", begin)
    accept = source.index("host.level.Accept(", activate)

    assert begin < activate < accept
    assert 'candidate.Get("cam")' in source


def test_initial_load_replaces_null_scene_without_camera_deletion():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "load"
        / "load_clip.py"
    ).read_text(encoding="utf-8")

    assert 'Get("readerType")) == "0"' in source
    assert "NewSceneAndShot(path, 0.0)" in source


def test_loader_never_renames_shot_image_source():
    """A SynthEyes shot name is its footage/IFL path, not a UI label."""
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "load"
        / "load_clip.py"
    ).read_text(encoding="utf-8")

    assert "shot.SetName(" not in source


def test_loader_sets_detected_sequence_length():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "plugins"
        / "load"
        / "load_clip.py"
    ).read_text(encoding="utf-8")

    assert 'shot.Get("actualLength")' in source
    assert 'shot.Set("frameCount", actual_length)' in source
