"""Render SynthEyes Perspective viewport review sequences."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import ClassVar

import pyblish.api
from ayon_core.pipeline import PublishError

from ayon_syntheyes.api import SynthEyesHost
from ayon_syntheyes.api.review import (
    collect_review_files,
    review_filename,
    validate_image_extension,
)


class ExtractReview(pyblish.api.InstancePlugin):
    """Render a created review using Perspective Preview Movie."""

    order = pyblish.api.ExtractorOrder - 0.2
    hosts: ClassVar[list[str]] = ["syntheyes"]
    families: ClassVar[list[str]] = ["review"]
    label = "Render SynthEyes Review"

    file_extension = "jpg"
    show_all_viewport_items = False
    show_grid = False
    square_pixel_output = True
    anti_aliasing_motion_blur = "Medium"
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
            extension = validate_image_extension(self.file_extension)
        except ValueError as exc:
            raise PublishError(str(exc)) from exc

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
        product_name = instance.data["productName"]
        staging_dir = Path(
            tempfile.mkdtemp(prefix=f"ayon_syntheyes_{product_name}_")
        )
        output_file = staging_dir / review_filename(
            product_name,
            frame_start,
            extension,
        )

        options = {
            "show_all_viewport_items": self.show_all_viewport_items,
            "show_grid": self.show_grid,
            "square_pixel_output": self.square_pixel_output,
            "anti_aliasing_motion_blur": self.anti_aliasing_motion_blur,
            "shutter_angle": self.shutter_angle,
            "phase": self.phase,
            "frame_time_burnin": self.frame_time_burnin,
        }
        host.render_review(str(output_file), options)
        files = collect_review_files(staging_dir, extension)
        if not files:
            raise PublishError(
                f"SynthEyes did not render any '.{extension}' review frames "
                f"to '{staging_dir}'."
            )

        instance.data.update(
            {
                "family": "review",
                "families": list(
                    set(instance.data.get("families", [])) | {"review"}
                ),
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "representations": [
                    {
                        "name": extension,
                        "ext": extension,
                        "files": [path.name for path in files],
                        "stagingDir": str(staging_dir),
                        "tags": list(self.tags),
                    }
                ],
            }
        )
