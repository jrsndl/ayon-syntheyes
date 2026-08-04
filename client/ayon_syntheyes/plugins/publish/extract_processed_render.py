"""Render processed plate sequences from SynthEyes."""

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


class ExtractProcessedRender(pyblish.api.InstancePlugin):
    """Use Image Preprocessor Save Sequence for a render product."""

    order = pyblish.api.ExtractorOrder - 0.2
    hosts: ClassVar[list[str]] = ["syntheyes"]
    families: ClassVar[list[str]] = ["render"]
    label = "Render SynthEyes Processed Plate"

    reset_filtering_color = True
    file_extension = "jpg"
    rgb_included = True
    alpha_included = False
    meshes_included = False
    frame_time_burnin = False
    tags = ["review"]

    @classmethod
    def apply_settings(cls, project_settings: dict) -> None:
        settings = (
            project_settings.get("syntheyes", {})
            .get("create", {})
            .get("CreateRender", {})
        )
        for key in (
            "reset_filtering_color",
            "file_extension",
            "rgb_included",
            "alpha_included",
            "meshes_included",
            "frame_time_burnin",
            "tags",
        ):
            if key in settings:
                setattr(cls, key, settings[key])

    def process(self, instance: pyblish.api.Instance) -> None:
        host = SynthEyesHost.get_host()
        if host is None:
            raise PublishError("The SynthEyes host is not installed.")
        creator_attributes = instance.data.get("creator_attributes") or {}
        file_extension = creator_attributes.get(
            "file_extension", self.file_extension
        )
        reset_filtering_color = creator_attributes.get(
            "reset_filtering_color", self.reset_filtering_color
        )
        try:
            extension = validate_image_extension(file_extension)
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
        host.render_processed_sequence(
            str(output_file),
            {
                "reset_filtering_color": reset_filtering_color,
                "rgb_included": self.rgb_included,
                "alpha_included": self.alpha_included,
                "meshes_included": self.meshes_included,
                "frame_time_burnin": self.frame_time_burnin,
            },
        )
        files = collect_review_files(staging_dir, extension)
        if not files:
            raise PublishError(
                f"SynthEyes did not render any '.{extension}' processed "
                f"frames to '{staging_dir}'."
            )

        colorspace = self._active_plate_colorspace(host)
        families = set(instance.data.get("families", []))
        families.add("render")
        if "review" in self.tags:
            families.add("review")
        instance.data.update(
            {
                "family": "render",
                "families": list(families),
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "colorspace": colorspace,
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

    @staticmethod
    def _active_plate_colorspace(host: SynthEyesHost) -> str | None:
        shot_id = str(
            host.level.Active().Get("cam").Get("shot").Get("uniqueID")
        )
        for container in host.get_containers():
            if (
                str(container.get("shot_id")) == shot_id
                and container.get("colorspace")
            ):
                return str(container["colorspace"])
        return None
