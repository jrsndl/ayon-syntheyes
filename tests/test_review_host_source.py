from pathlib import Path


def test_review_forces_full_detected_shot_range_and_restores_it():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "api"
        / "host.py"
    ).read_text(encoding="utf-8")
    review_source = source[source.index("    def render_review(") :]
    review_source = review_source[: review_source.index("    def render_processed_sequence(")]

    assert 'actual_length = int(shot.Get("actualLength"))' in review_source
    assert 'shot.Set("frameCount", actual_length)' in review_source
    assert 'shot.Set("start", render_start)' in review_source
    assert 'shot.Set("stop", render_end)' in review_source
    assert "self.level.SetAnimStart(render_start)" in review_source
    assert "self.level.SetAnimEnd(render_end)" in review_source
    assert "self.level.SetAnimStart(previous_anim_start)" in review_source
    assert "self.level.SetAnimEnd(previous_anim_end)" in review_source
    assert "start.ClickAndContinue()" in review_source
    assert "self._wait_for_review_movie" in review_source
    assert "_is_finalized_mov" in review_source
    assert "self._wait_for_image_sequence" in review_source
    assert 'Path(options["last_output_file"])' in review_source


def test_processed_render_waits_for_final_frame_before_restoring():
    source = (
        Path(__file__).parents[1]
        / "client"
        / "ayon_syntheyes"
        / "api"
        / "host.py"
    ).read_text(encoding="utf-8")
    processed_source = source[source.index("    def render_processed_sequence(") :]
    processed_source = processed_source[: processed_source.index(
        "    def _resolve_exporter("
    )]

    assert 'actual_length = int(shot.Get("actualLength"))' in processed_source
    assert "last_frame = first_frame + actual_length - 1" in processed_source
    assert "start.ClickAndContinue()" in processed_source
    assert (
        "self._wait_for_image_sequence(last_output, actual_length)"
        in processed_source
    )
