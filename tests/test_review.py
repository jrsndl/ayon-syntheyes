"""Tests for SynthEyes review sequence helpers."""

import pytest

from ayon_syntheyes.api.review import (
    collect_review_files,
    review_filename,
    validate_image_extension,
)


def test_review_extension_accepts_images_only():
    assert validate_image_extension(".PNG") == "png"
    with pytest.raises(ValueError, match="container formats"):
        validate_image_extension("mov")


def test_review_filename_uses_numbered_image_sequence():
    assert review_filename("reviewMain", 1001, "jpg") == (
        "reviewMain.1001.jpg"
    )


def test_collect_review_files_filters_and_sorts(tmp_path):
    second = tmp_path / "reviewMain.1002.PNG"
    first = tmp_path / "reviewMain.1001.png"
    second.write_text("2", encoding="utf-8")
    first.write_text("1", encoding="utf-8")
    (tmp_path / "reviewMain.mov").write_text("movie", encoding="utf-8")
    assert collect_review_files(tmp_path, "png") == [first, second]
