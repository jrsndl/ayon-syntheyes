"""Tests for SynthEyes review sequence helpers."""

import pytest

from ayon_syntheyes.api.review import (
    collect_review_files,
    collect_review_movie,
    native_review_sequence_filename,
    review_filename,
    review_movie_filename,
    validate_image_extension,
    validate_review_output_extension,
    validate_review_extension,
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


def test_review_output_accepts_only_mov():
    assert validate_review_extension(".MOV") == "mov"
    with pytest.raises(ValueError, match="must use the '.mov'"):
        validate_review_extension("jpg")


def test_review_native_output_allows_safe_sequence_extensions():
    assert validate_review_output_extension(".DPX") == "dpx"
    assert validate_review_output_extension("bmp") == "bmp"
    assert native_review_sequence_filename("reviewMain", 1001, "dpx") == (
        "reviewMain.1001.dpx"
    )
    with pytest.raises(ValueError, match="letters and digits"):
        validate_review_output_extension("../mov")


def test_review_movie_is_a_single_exact_file(tmp_path):
    filename = review_movie_filename("reviewMain")
    movie = tmp_path / filename
    movie.write_text("movie", encoding="utf-8")
    (tmp_path / "other.mov").write_text("other", encoding="utf-8")
    assert filename == "reviewMain.mov"
    assert collect_review_movie(tmp_path, filename) == movie
