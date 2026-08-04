"""Render a SynthEyes Perspective viewport review to ProRes MOV."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import ClassVar

import pyblish.api
from ayon_core.pipeline import PublishError

from ayon_syntheyes.api import SynthEyesHost
from ayon_syntheyes.api.review import (
    collect_review_files,
    collect_review_movie,
    native_review_sequence_filename,
    review_movie_filename,
    validate_review_output_extension,
    validate_review_extension,
)


class ExtractReview(pyblish.api.InstancePlugin):
    """Render a created review using Perspective Preview Movie."""

    order = pyblish.api.ExtractorOrder - 0.2
    hosts: ClassVar[list[str]] = ["syntheyes"]
    families: ClassVar[list[str]] = ["review"]
    label = "Render SynthEyes Review"

    file_extension = "mov"
    compression = "ProRes"
    show_all_viewport_items = False
    show_grid = False
    square_pixel_output = True
    anti_aliasing_motion_blur = "None"
    shutter_angle = 180.0
    phase = -90.0
    frame_time_burnin = True
    tags = ["review"]

    @classmethod
    def apply_settings(cls, project_settings: dict) -> None:
        settings = (
            project_settings.get("syntheyes", {})
            .get("create", {})
            .get("CreateReview", {})
        )
        for key in (
            "file_extension",
            "compression",
            "show_all_viewport_items",
            "show_grid",
            "square_pixel_output",
            "anti_aliasing_motion_blur",
            "shutter_angle",
            "phase",
            "frame_time_burnin",
            "tags",
        ):
            if key in settings:
                setattr(cls, key, settings[key])

    def process(self, instance: pyblish.api.Instance) -> None:
        host = SynthEyesHost.get_host()
        if host is None:
            raise PublishError("The SynthEyes host is not installed.")
        try:
            extension = validate_review_output_extension(self.file_extension)
        except ValueError as exc:
            raise PublishError(str(exc)) from exc
        is_movie = extension == "mov"
        if is_movie:
            validate_review_extension(extension)

        frame_start = int(
            instance.data.get(
                "frameStart",
                instance.context.data.get("frameStart", host.level.AnimStart()),
            )
        )
        frame_end = int(
            instance.data.get(
                "frameEnd",
                instance.context.data.get("frameEnd", host.level.AnimEnd()),
            )
        )
        active_shot = host.level.Active().Get("cam").Get("shot")
        fps = float(
            instance.data.get(
                "fps",
                instance.context.data.get("fps", active_shot.Get("rate")),
            )
        )
        product_name = instance.data["productName"]
        staging_dir = Path(
            tempfile.mkdtemp(prefix=f"ayon_syntheyes_{product_name}_")
        )
        if is_movie:
            output_file = staging_dir / review_movie_filename(
                product_name, extension
            )
            last_output_file = output_file
        else:
            output_file = staging_dir / native_review_sequence_filename(
                product_name, frame_start, extension
            )
            last_output_file = staging_dir / native_review_sequence_filename(
                product_name, frame_end, extension
            )

        options = {
            "show_all_viewport_items": self.show_all_viewport_items,
            "show_grid": self.show_grid,
            "square_pixel_output": self.square_pixel_output,
            "anti_aliasing_motion_blur": self.anti_aliasing_motion_blur,
            "shutter_angle": self.shutter_angle,
            "phase": self.phase,
            "frame_time_burnin": self.frame_time_burnin,
            "compression": self.compression,
            "last_output_file": str(last_output_file),
        }
        host.render_review(str(output_file), options)
        if is_movie:
            movie = collect_review_movie(staging_dir, output_file.name)
            if movie is None:
                raise PublishError(
                    f"SynthEyes did not render the ProRes review movie "
                    f"to '{staging_dir}'."
                )
            representation_files = movie.name
        else:
            files = collect_review_files(staging_dir, extension)
            if not files:
                raise PublishError(
                    f"SynthEyes did not render any '.{extension}' review "
                    f"frames to '{staging_dir}'."
                )
            representation_files = [path.name for path in files]

        instance.data.update(
            {
                "family": "review",
                "families": list(
                    set(instance.data.get("families", [])) | {"review"}
                ),
                "productBaseType": "review",
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": fps,
            }
        )
        instance.data.setdefault("representations", []).append(
            {
                "name": extension,
                "ext": extension,
                "files": representation_files,
                "stagingDir": str(staging_dir),
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": fps,
                "tags": list(self.tags),
            }
        )
