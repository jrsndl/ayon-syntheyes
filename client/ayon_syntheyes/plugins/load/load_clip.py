"""Load AYON plates and renders as SynthEyes shots."""

from __future__ import annotations

import os
from typing import Any, ClassVar, Optional

from ayon_core.lib.transcoding import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ayon_core.pipeline import get_representation_path, load

from ayon_syntheyes.api import Container, SynthEyesHost
from ayon_syntheyes.api.clip import (
    DEPTH_VALUES,
    OUTPUT_DEPTH_VALUES,
    entity_fps,
)


def _version_number(context: dict[str, Any]) -> Optional[str]:
    version = context.get("version") or {}
    value = version.get("version")
    return None if value is None else str(value)


class LoadClip(load.LoaderPlugin):
    """Load a plate or render representation as a non-stereo shot."""

    product_base_types: ClassVar[set[str]] = {"plate", "render"}
    product_types = product_base_types
    representations: ClassVar[set[str]] = {"*"}
    extensions: ClassVar[set[str]] = {
        extension.lstrip(".").lower()
        for extension in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
    }
    label = "Load clip"
    order = -10
    icon = "image"
    color = "orange"

    match_frame_numbers = True
    process_depth = "Half"
    output_depth = "Half"
    lut_3d = "None"
    levels = [0.0, 0.5, 1.0]

    @classmethod
    def apply_settings(
        cls,
        project_settings: dict,
    ) -> None:
        """Apply project-level clip defaults to the discovered plugin."""
        super().apply_settings(project_settings)
        settings = project_settings.get("syntheyes", {}).get("load_clip", {})
        cls.match_frame_numbers = settings.get(
            "match_frame_numbers", cls.match_frame_numbers
        )
        cls.process_depth = settings.get(
            "process_depth", cls.process_depth
        )
        cls.output_depth = settings.get(
            "output_depth", cls.output_depth
        )
        cls.lut_3d = settings.get("lut_3d", cls.lut_3d)
        level_settings = settings.get("level_adjustment", {})
        cls.levels = [
            float(level_settings.get("low", cls.levels[0])),
            float(level_settings.get("mid", cls.levels[1])),
            float(level_settings.get("high", cls.levels[2])),
        ]

    def load(
        self,
        context: dict,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> dict:
        """Create and configure a SynthEyes shot."""
        host = self._host()
        path = self._representation_path(context)
        shot_name = namespace or name or self._default_name(context)
        existing_shots = host.level.Shots()
        replace_empty_scene = (
            len(existing_shots) == 1
            and str(existing_shots[0].Get("readerType")) == "0"
        )
        shot = self._add_shot(
            host,
            path,
            shot_name,
            entity_fps(context),
            replace_empty_scene=replace_empty_scene,
        )
        container = self._container(context, shot, shot_name)
        host.add_container(container)
        return {"shot": shot, "container": container}

    def update(self, container: dict, context: dict) -> dict:
        """Replace a loaded shot with another representation version."""
        host = self._host()
        path = self._representation_path(context)
        shot_name = container["namespace"]
        shot = self._add_shot(
            host,
            path,
            shot_name,
            entity_fps(context),
            replace_shot_ids=(
                {str(container["shot_id"])}
                if container.get("shot_id")
                else set()
            ),
        )
        updated = self._container(context, shot, shot_name)
        host.add_container(updated)
        return {"shot": shot, "container": updated}

    def switch(self, container: dict, context: dict) -> dict:
        """Switch uses the same replacement behavior as update."""
        return self.update(container, context)

    def remove(self, container: dict) -> None:
        """Remove the SynthEyes shot and its AYON container record."""
        host = self._host()
        self._delete_shot(host, container.get("shot_id"))
        host.remove_container(container["namespace"])

    def _add_shot(
        self,
        host: SynthEyesHost,
        path: str,
        name: str,
        fps: float,
        replace_shot_ids: Optional[set[str]] = None,
        replace_empty_scene: bool = False,
    ) -> Any:
        replace_shot_ids = replace_shot_ids or set()
        previous_info = None
        previous_workfile = None
        if replace_empty_scene:
            # Deleting SynthEyes' live placeholder camera can trigger its
            # imminent-crash handler. Replace the empty scene through the
            # purpose-built API instead, retaining AYON metadata and the
            # current Workfiles path.
            previous_info = host.level.Scene().Get("info") or ""
            previous_workfile = host.level.SNIFileName() or ""
            shot = host.level.NewSceneAndShot(path, 0.0)
            if previous_workfile:
                host.level.SetSNIFileName(previous_workfile)
        else:
            # AddShot is intentionally used instead of AddStereoShot.
            shot = host.level.AddShot(path, 0.0)
        if shot is None:
            raise RuntimeError(f"SynthEyes failed to load clip '{path}'.")

        host.level.BeginShotChanges(shot)
        try:
            # SynthEyes initializes scripted shots with a 10-frame working
            # range. Boris' SyPy documentation explicitly requires copying
            # the detected reader length into frameCount after opening.
            actual_length = int(shot.Get("actualLength"))
            if actual_length > 0:
                shot.Set("frameCount", actual_length)
            shot.Set("matchFrameNumbers", int(self.match_frame_numbers))
            shot.Set("rate", float(fps))
            shot.Set("processFormat", DEPTH_VALUES[self.process_depth])
            shot.Set("storeFormat", OUTPUT_DEPTH_VALUES[self.output_depth])

            live = shot.Get("live")
            live.Set("vrmode", 0)
            live.Set("colormapName", "" if self.lut_3d == "None" else self.lut_3d)
            live.Set("levels", list(self.levels))
        except Exception:
            host.level.Cancel()
            raise
        else:
            host.level.AcceptShotChanges(shot, f"AYON load {name}")

        if previous_info is not None:
            host.level.Begin()
            try:
                host.level.Scene().Set("info", previous_info)
            except Exception:
                host.level.Cancel()
                raise
            else:
                host.level.Accept("Restore AYON scene information")

        # SetActive must be inside a regular undo block. AddShot briefly shows
        # the imported image but leaves the previous tracker host active after
        # AcceptShotChanges, which makes a successful load look as if it
        # disappeared. Delete only the explicitly replaced shots (or null
        # reader placeholders collected before AddShot).
        if not replace_empty_scene:
            host.level.Begin()
            try:
                host.level.SetActive(shot.Get("cam"))
                for candidate in host.level.Shots():
                    if str(candidate.Get("uniqueID")) in replace_shot_ids:
                        host.level.Delete(candidate.Get("cam"))
                host.level.ReloadAll()
            except Exception:
                host.level.Cancel()
                raise
            else:
                host.level.Accept(f"Activate AYON clip {name}")
        return shot

    @staticmethod
    def _delete_shot(host: SynthEyesHost, shot_id: Optional[str]) -> None:
        if not shot_id:
            return
        shot = next(
            (
                candidate
                for candidate in host.level.Shots()
                if str(candidate.Get("uniqueID")) == str(shot_id)
            ),
            None,
        )
        if shot is None:
            return
        host.level.Begin()
        try:
            host.level.Delete(shot.Get("cam"))
        except Exception:
            host.level.Cancel()
            raise
        else:
            host.level.Accept("AYON remove clip")
            host.level.ReloadAll()

    def _container(
        self,
        context: dict,
        shot: Any,
        shot_name: str,
    ) -> Container:
        representation = context["representation"]
        return Container(
            name=shot_name,
            namespace=shot_name,
            loader=self.__class__.__name__,
            representation=str(representation["id"]),
            objectName=shot_name,
            version=_version_number(context),
            shot_id=str(shot.Get("uniqueID")),
            colorspace=self._colorspace(context),
        )

    @staticmethod
    def _colorspace(context: dict) -> Optional[str]:
        """Extract AYON colorspace metadata from the loaded representation."""
        representation = context.get("representation") or {}
        colorspace_data = representation.get("colorspaceData") or {}
        for source in (
            colorspace_data,
            representation,
            representation.get("data") or {},
            representation.get("attrib") or {},
            context.get("version") or {},
        ):
            value = source.get("colorspace")
            if value:
                return str(value)
        return None

    @staticmethod
    def _host() -> SynthEyesHost:
        host = SynthEyesHost.get_host()
        if host is None:
            raise RuntimeError("The SynthEyes host is not installed.")
        return host

    def _representation_path(self, context: dict) -> str:
        path = self.filepath_from_context(context)
        if not path:
            path = get_representation_path(context["representation"])
        path = os.path.normpath(path)
        if not os.path.exists(path):
            raise RuntimeError(f"Representation path does not exist: {path}")
        return path

    @staticmethod
    def _default_name(context: dict) -> str:
        product = context.get("product") or {}
        return product.get("name") or "AYON Clip"
