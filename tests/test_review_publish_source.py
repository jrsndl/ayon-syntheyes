from pathlib import Path


ROOT = Path(__file__).parents[1] / "client" / "ayon_syntheyes"


def test_review_representation_has_core_review_metadata():
    source = (
        ROOT / "plugins" / "publish" / "extract_review.py"
    ).read_text(encoding="utf-8")

    assert '"productBaseType": "review"' in source
    assert '"frameStart": frame_start' in source
    assert '"frameEnd": frame_end' in source
    assert '"fps": fps' in source
    assert 'setdefault("representations", []).append(' in source
    assert "collect_review_movie" in source
    assert "collect_review_files" in source


def test_review_instance_is_reasserted_after_integration():
    source = (
        ROOT / "plugins" / "publish" / "integrate_persist_review.py"
    ).read_text(encoding="utf-8")

    assert "pyblish.api.IntegratorOrder + 0.49" in source
    assert "host.keep_publish_instance" in source
