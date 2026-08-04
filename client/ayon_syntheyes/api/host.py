"""AYON host implementation backed by an external SyPy connection."""

from __future__ import annotations

import dataclasses
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import pyblish.api
from ayon_core.host import HostBase, ILoadHost, IPublishHost, IWorkfileHost
from ayon_core.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
)

from ayon_syntheyes import SYNTH_EYES_HOST_DIR
from ayon_syntheyes.api.pipeline import Container

PUBLISH_PATH = os.path.join(SYNTH_EYES_HOST_DIR, "plugins", "publish")
LOAD_PATH = os.path.join(SYNTH_EYES_HOST_DIR, "plugins", "load")
CREATE_PATH = os.path.join(SYNTH_EYES_HOST_DIR, "plugins", "create")
AYON_METADATA_GUARD = "AYON_CONTEXT::{}::AYON_CONTEXT_END"
AYON_METADATA_REGEX = re.compile(
    AYON_METADATA_GUARD.format(r"(?P<context>.*?)"),
    re.DOTALL,
)


class SynthEyesHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    """AYON host facade for a connected SynthEyes application."""

    name = "syntheyes"
    _instance = None

    def __init__(self, level: Any) -> None:
        super().__init__()
        self.level = level
        self._main_window = None
        self._transient_metadata = {}
        SynthEyesHost._instance = self

    @classmethod
    def get_host(cls) -> Optional["SynthEyesHost"]:
        return cls._instance

    def install(self) -> None:
        pyblish.api.register_host(self.name)
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

    def set_main_window(self, window: Any) -> None:
        self._main_window = window

    def get_main_window(self) -> Any:
        return self._main_window

    def get_workfile_extensions(self) -> list[str]:
        return [".sni"]

    def get_current_workfile(self) -> str:
        return self.level.SNIFileName() or ""

    def workfile_has_unsaved_changes(self) -> bool:
        # SyPy only exposes the interactive SaveIfChanged operation. There is
        # no non-mutating dirty-state query in the 2026 public API.
        return True

    def open_workfile(self, filepath: str) -> str:
        path = os.path.abspath(filepath)
        result_count = self.level.OpenSNI(path)
        if result_count == 0:
            raise RuntimeError(f"SynthEyes failed to open '{path}'.")
        return path

    def save_workfile(self, dst_path: Optional[str] = None) -> str:
        requested_path = dst_path or self.get_current_workfile()
        if not requested_path:
            raise RuntimeError("A destination is required for an unsaved scene.")
        path = os.path.abspath(requested_path)
        self.level.SetSNIFileName(path)
        self.level.ClickTopMenuAndWait("File", "Save")
        if not os.path.isfile(path):
            raise RuntimeError(
                f"SynthEyes did not create the workfile '{path}'."
            )
        return path

    def _click_action(self, action: str) -> None:
        action_id = self.level.ActionID(action)
        if action_id is None or int(action_id) < 0:
            raise RuntimeError(f"SynthEyes action is unavailable: {action}")
        self.level.Main().ByID(action_id).ClickAndWait()

    def get_context_data(self) -> dict:
        return self._read_metadata().get("context", {})

    def update_context_data(self, data: dict, changes: dict) -> None:
        metadata = self._read_metadata()
        metadata["context"] = data
        self._write_metadata(metadata)

    def get_publish_instances(self) -> list[dict]:
        return self._read_metadata().get("publish_instances", [])

    def get_containers(self):
        """Yield valid loaded representation records."""
        for container in self._read_metadata().get("containers", []):
            if container.get("name") and container.get("namespace"):
                yield container

    def add_container(self, container: Container) -> None:
        metadata = self._read_metadata()
        containers = [
            item
            for item in self.get_containers()
            if item.get("namespace") != container.namespace
        ]
        containers.append(dataclasses.asdict(container))
        metadata["containers"] = containers
        self._write_metadata(metadata)

    def remove_container(self, namespace: str) -> None:
        metadata = self._read_metadata()
        metadata["containers"] = [
            item
            for item in self.get_containers()
            if item.get("namespace") != namespace
        ]
        self._write_metadata(metadata)

    def write_create_instances(self, instances: list[dict]) -> None:
        metadata = self._read_metadata()
        metadata["publish_instances"] = instances
        self._write_metadata(metadata)

    def add_publish_instance(self, instance_data: dict) -> None:
        instances = self.get_publish_instances()
        instances.append(instance_data)
        self.write_create_instances(instances)

    def update_publish_instance(
        self,
        instance_id: str,
        data: dict,
    ) -> None:
        instances = self.get_publish_instances()
        for index, item in enumerate(instances):
            if item.get("instance_id") == instance_id:
                instances[index] = data
                break
        self.write_create_instances(instances)

    def remove_create_instance(self, instance_id: str) -> None:
        instances = [
            item
            for item in self.get_publish_instances()
            if item.get("instance_id") != instance_id
        ]
        self.write_create_instances(instances)

    def keep_publish_instance(self, instance_id: str) -> bool:
        """Keep a creator instance active after a successful publish."""
        instances = self.get_publish_instances()
        found = False
        for item in instances:
            if item.get("instance_id") != instance_id:
                continue
            item["active"] = True
            item["followWorkfileVersion"] = True
            item["productBaseType"] = "review"
            item["productType"] = "review"
            found = True
            break
        if found:
            self.write_create_instances(instances)
        return found

    def _read_metadata(self) -> dict:
        description = self.level.Scene().Get("info") or ""
        match = AYON_METADATA_REGEX.search(description)
        if not match:
            return dict(self._transient_metadata)
        try:
            value = json.loads(match.group("context"))
        except ValueError:
            self.log.warning("AYON metadata in Scene Information is invalid.")
            return {}
        return value if isinstance(value, dict) else {}

    def _write_metadata(self, data: dict) -> None:
        scene = self.level.Scene()
        description = scene.Get("info") or ""
        encoded = json.dumps(data, indent=2, sort_keys=True)
        guarded = AYON_METADATA_GUARD.format(encoded)
        if AYON_METADATA_REGEX.search(description):
            description = AYON_METADATA_REGEX.sub(
                lambda _match: guarded,
                description,
            )
        else:
            separator = "\n" if description and not description.endswith("\n") else ""
            description = f"{description}{separator}{guarded}"

        self.level.Begin()
        try:
            scene.Set("info", description)
        except Exception:
            self.level.Cancel()
            raise
        else:
            self.level.Accept("Update AYON metadata")
            self._transient_metadata = {}

    def export_with_preset(
        self,
        exporter_script: str,
        preset_path: str,
        output_directory: str,
    ) -> None:
        """Run one native Multi-Export stage from a Workflow Preset JSON."""
        script_path, exporter_name = self._resolve_exporter(exporter_script)
        preset = Path(preset_path)
        if not preset.is_file():
            raise RuntimeError(
                f"SynthEyes Workflow Preset file does not exist: {preset}"
            )
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="ayon_syntheyes_") as temp_dir:
            temp_root = Path(temp_dir)
            backup_path = temp_root / "folder_preferences.json"
            configure_path = temp_root / "configure_export.szl"
            restore_path = temp_root / "restore_export.szl"
            configure_path.write_text(
                self._configuration_script(
                    preset, output, backup_path, exporter_name, script_path
                ),
                encoding="utf-8",
            )
            restore_path.write_text(
                self._restore_script(backup_path),
                encoding="utf-8",
            )
            self.level.RunScriptFile(str(configure_path))
            try:
                self.level.ExportMultiple()
            finally:
                self.level.RunScriptFile(str(restore_path))

    def render_review(
        self,
        output_file: str,
        options: dict,
    ) -> None:
        """Render a Perspective Preview Movie or image sequence."""
        output_path = Path(output_file)
        is_movie = output_path.suffix.lower() == ".mov"
        if is_movie and options.get("compression") != "ProRes":
            raise RuntimeError("SynthEyes MOV reviews must use ProRes.")
        active = self.level.Active()
        camera = active.Get("cam")
        shot = camera.Get("shot")
        scene = self.level.Scene()

        previous = {
            "previewFile": shot.Get("previewFile"),
            "shutterAngle": shot.Get("shutterAngle"),
            "shutterPhase": shot.Get("shutterPhase"),
            "frameCount": shot.Get("frameCount"),
            "start": shot.Get("start"),
            "stop": shot.Get("stop"),
            "burnInWhen": scene.Get("burnInWhen"),
        }
        previous_view = self.level.View()
        previous_anim_start = self.level.AnimStart()
        previous_anim_end = self.level.AnimEnd()
        actual_length = int(shot.Get("actualLength"))
        if actual_length < 1:
            raise RuntimeError("The active SynthEyes shot has no readable frames.")
        render_start = 0
        render_end = actual_length - 1
        self.level.BeginShotChanges(shot)
        try:
            shot.Set("previewFile", os.path.abspath(output_file))
            shot.Set("shutterAngle", float(options["shutter_angle"]))
            shot.Set("shutterPhase", float(options["phase"]))
            shot.Set("frameCount", actual_length)
            shot.Set("start", render_start)
            shot.Set("stop", render_end)
            burn_when = int(previous["burnInWhen"])
            if options["frame_time_burnin"]:
                burn_when |= 2
            else:
                burn_when &= ~2
            scene.Set("burnInWhen", burn_when)
        except Exception:
            self.level.Cancel()
            raise
        else:
            self.level.AcceptShotChanges(shot, "Configure AYON review")
        self.level.SetAnimStart(render_start)
        self.level.SetAnimEnd(render_end)

        popup = None
        try:
            self.level.SetView("Perspective")
            perspective = self.level.Main().ByClass("Perspect")
            if not perspective.IsValid():
                raise RuntimeError(
                    "SynthEyes Perspective viewport is unavailable."
                )
            perspective.PerformActionByNameAndContinue(
                "Persp/Preview Movie"
            )
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                popup = self.level.Popup()
                if (
                    popup.IsValid()
                    and popup.Name() == "Preview Movie Settings"
                ):
                    break
                time.sleep(0.05)
            if not popup.IsValid() or popup.Name() != "Preview Movie Settings":
                raise RuntimeError(
                    "SynthEyes did not open Preview Movie Settings."
                )

            checks = {
                1335: options["show_all_viewport_items"],
                1336: options["show_grid"],
                1337: options["square_pixel_output"],
                2352: options["frame_time_burnin"],
            }
            for control_id, value in checks.items():
                control = popup.ByID(control_id)
                if not control.IsValid():
                    raise RuntimeError(
                        f"Preview Movie control {control_id} is unavailable."
                    )
                control.SetChecked(int(value))

            quality = popup.ByID(1339)
            if not quality.IsValid():
                raise RuntimeError(
                    "Preview Movie anti-aliasing control is unavailable."
                )
            quality.SetOption(options["anti_aliasing_motion_blur"])

            start = popup.ByID(1)
            if not start.IsValid():
                raise RuntimeError(
                    "Preview Movie Start button is unavailable."
                )
            start.ClickAndContinue()
            if is_movie:
                self._wait_for_review_movie(output_path, actual_length)
            else:
                self._wait_for_image_sequence(
                    Path(options["last_output_file"]), actual_length
                )
        finally:
            if popup is not None and popup.IsValid():
                cancel = popup.ByID(2)
                if cancel.IsValid():
                    cancel.ClickAndWait()
            self.level.SetView(previous_view)
            self.level.SetAnimStart(previous_anim_start)
            self.level.SetAnimEnd(previous_anim_end)
            self.level.BeginShotChanges(shot)
            try:
                shot.Set("previewFile", previous["previewFile"])
                shot.Set("shutterAngle", previous["shutterAngle"])
                shot.Set("shutterPhase", previous["shutterPhase"])
                shot.Set("frameCount", previous["frameCount"])
                shot.Set("start", previous["start"])
                shot.Set("stop", previous["stop"])
                scene.Set("burnInWhen", previous["burnInWhen"])
            except Exception:
                self.level.Cancel()
                raise
            else:
                self.level.AcceptShotChanges(
                    shot, "Restore Preview Movie settings"
                )

    @staticmethod
    def _is_finalized_mov(path: Path) -> bool:
        """Return whether MOV has complete atoms and a moov atom."""
        try:
            file_size = path.stat().st_size
            with path.open("rb") as stream:
                offset = 0
                found_moov = False
                while offset < file_size:
                    stream.seek(offset)
                    header = stream.read(8)
                    if len(header) != 8:
                        return False
                    atom_size = int.from_bytes(header[:4], "big")
                    atom_type = header[4:8]
                    header_size = 8
                    if atom_size == 1:
                        extended = stream.read(8)
                        if len(extended) != 8:
                            return False
                        atom_size = int.from_bytes(extended, "big")
                        header_size = 16
                    elif atom_size == 0:
                        atom_size = file_size - offset
                    if (
                        atom_size < header_size
                        or offset + atom_size > file_size
                    ):
                        return False
                    found_moov = found_moov or atom_type == b"moov"
                    offset += atom_size
                return found_moov and offset == file_size
        except OSError:
            return False

    @staticmethod
    def _wait_for_review_movie(path: Path, frame_count: int) -> None:
        """Wait for Preview Movie without touching SyPy during encoding."""
        timeout = min(1800.0, max(300.0, float(frame_count) * 10.0))
        deadline = time.monotonic() + timeout
        last_size = -1
        stable_since = None
        while time.monotonic() < deadline:
            try:
                size = path.stat().st_size
            except OSError:
                size = -1

            if (
                size >= 4096
                and size == last_size
                and SynthEyesHost._is_finalized_mov(path)
            ):
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= 5.0:
                    return
            else:
                stable_since = None
            last_size = size
            time.sleep(0.5)

        raise RuntimeError(
            f"Timed out after {timeout:.0f}s waiting for SynthEyes to "
            f"finalize '{path}'. Last observed size: {last_size} bytes."
        )

    @staticmethod
    def _wait_for_image_sequence(path: Path, frame_count: int) -> None:
        """Wait for the expected final frame without touching SyPy."""
        timeout = min(1800.0, max(300.0, float(frame_count) * 10.0))
        deadline = time.monotonic() + timeout
        last_size = -1
        stable_since = None
        while time.monotonic() < deadline:
            try:
                size = path.stat().st_size
            except OSError:
                size = -1

            if size > 0 and size == last_size:
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= 2.0:
                    return
            else:
                stable_since = None
            last_size = size
            time.sleep(0.5)

        raise RuntimeError(
            f"Timed out after {timeout:.0f}s waiting for the last SynthEyes "
            f"review frame '{path}'. Last observed size: {last_size} bytes."
        )

    def render_processed_sequence(
        self,
        output_file: str,
        options: dict,
    ) -> None:
        """Render the active shot through Image Preprocessor Save Sequence."""
        active = self.level.Active()
        shot = active.Get("cam").Get("shot")
        scene = self.level.Scene()
        output = Path(output_file)
        output.parent.mkdir(parents=True, exist_ok=True)
        actual_length = int(shot.Get("actualLength"))
        if actual_length < 1:
            raise RuntimeError("The active SynthEyes shot has no frames.")
        frame_match = re.match(r"^(.*?)(\d+)$", output.stem)
        if frame_match is None:
            raise RuntimeError(
                "Processed sequence filename must end in a frame number: "
                f"{output.name}"
            )
        first_frame = int(frame_match.group(2))
        frame_width = len(frame_match.group(2))
        last_frame = first_frame + actual_length - 1
        last_output = output.with_name(
            f"{frame_match.group(1)}{last_frame:0{frame_width}d}"
            f"{output.suffix}"
        )
        previous = {
            "renderFile": shot.Get("renderFile"),
            "renderSettings": shot.Get("renderSettings"),
            "burnInWhen": scene.Get("burnInWhen"),
        }

        token = secrets.token_hex(8)
        original_name = f"AYON_original_{token}"
        defaults_name = f"AYON_defaults_{token}"
        popup = None
        with tempfile.TemporaryDirectory(
            prefix="ayon_syntheyes_render_"
        ) as temp_dir:
            temp_root = Path(temp_dir)
            prepare_path = temp_root / "prepare_processed_render.szl"
            restore_path = temp_root / "restore_processed_render.szl"
            prepare_path.write_text(
                self._prepare_image_preprocessor_script(
                    original_name,
                    defaults_name,
                ),
                encoding="utf-8",
            )
            restore_path.write_text(
                self._restore_image_preprocessor_script(
                    original_name,
                    defaults_name,
                ),
                encoding="utf-8",
            )

            try:
                if options["reset_filtering_color"]:
                    self.level.RunScriptFile(str(prepare_path))

                self.level.Begin()
                try:
                    shot.Set("renderFile", str(output.resolve()))
                    burn_when = int(previous["burnInWhen"])
                    if options["frame_time_burnin"]:
                        burn_when |= 8
                    else:
                        burn_when &= ~8
                    scene.Set("burnInWhen", burn_when)
                except Exception:
                    self.level.Cancel()
                    raise
                else:
                    self.level.Accept("Configure AYON processed render")

                self.level.PerformActionByNameAndContinue("Save Sequence")
                deadline = time.monotonic() + 10.0
                while time.monotonic() < deadline:
                    popup = self.level.Popup()
                    if (
                        popup.IsValid()
                        and popup.Name()
                        == "Save Processed Image Sequence"
                    ):
                        break
                    time.sleep(0.05)
                if (
                    popup is None
                    or not popup.IsValid()
                    or popup.Name() != "Save Processed Image Sequence"
                ):
                    raise RuntimeError(
                        "SynthEyes did not open Save Processed Image Sequence."
                    )

                checks = {
                    1346: options["rgb_included"],
                    1570: options["alpha_included"],
                    2250: options["meshes_included"],
                    2352: options["frame_time_burnin"],
                }
                for control_id, value in checks.items():
                    control = popup.ByID(control_id)
                    if not control.IsValid():
                        raise RuntimeError(
                            f"Save Sequence control {control_id} is "
                            "unavailable."
                        )
                    control.SetChecked(int(value))

                start = popup.ByID(1)
                if not start.IsValid():
                    raise RuntimeError(
                        "Save Sequence Start button is unavailable."
                    )
                start.ClickAndContinue()
                self._wait_for_image_sequence(last_output, actual_length)
            finally:
                if popup is not None and popup.IsValid():
                    close = popup.ByID(2)
                    if close.IsValid():
                        close.ClickAndWait()
                if options["reset_filtering_color"]:
                    self.level.RunScriptFile(str(restore_path))
                self.level.Begin()
                try:
                    shot.Set("renderFile", previous["renderFile"])
                    shot.Set("renderSettings", previous["renderSettings"])
                    scene.Set("burnInWhen", previous["burnInWhen"])
                except Exception:
                    self.level.Cancel()
                    raise
                else:
                    self.level.Accept("Restore Save Sequence settings")

    @staticmethod
    def _prepare_image_preprocessor_script(
        original_name: str,
        defaults_name: str,
    ) -> str:
        return f'''//SIZZLET AYON Prepare Processed Plate
shot = Scene.activeObject.cam.shot
priorID = ""
for (preset in shot.preset)
    if (preset.active)
        priorID = preset.uniqueID
    end
end
original = new shot.preset
original.nm = "{original_name}"
original.description = priorID
original.Disconnect()
shot.live.ResetPreset()
defaults = new shot.preset
defaults.nm = "{defaults_name}"
defaults.Disconnect()
original.affects = 63
original.Activate()
defaults.affects = 6
defaults.Activate()
shot.RegenAspect()
shot.Validate()
'''

    @staticmethod
    def _restore_image_preprocessor_script(
        original_name: str,
        defaults_name: str,
    ) -> str:
        return f'''//SIZZLET AYON Restore Processed Plate
shot = Scene.activeObject.cam.shot
original = null
defaults = null
prior = null
for (preset in shot.preset)
    if (preset.nm == "{original_name}")
        original = preset
    elseif (preset.nm == "{defaults_name}")
        defaults = preset
    end
end
if (!isNull(original))
    priorID = original.description
    for (preset in shot.preset)
        if (preset.uniqueID == priorID)
            prior = preset
        end
    end
    original.affects = 63
    original.Activate()
    original.Deactivate()
end
if (!isNull(prior))
    prior.Activate()
end
if (!isNull(defaults))
    delete defaults
end
if (!isNull(original))
    delete original
end
shot.RegenAspect()
shot.Validate()
'''

    def _resolve_exporter(self, exporter_script: str) -> tuple[Path, str]:
        scripts_root = Path(self.level.AppDir()) / "scripts"
        requested = Path(exporter_script.replace("\\", "/"))
        candidates = []
        direct = scripts_root / requested
        if direct.is_file():
            candidates = [direct]
        else:
            candidates = list(scripts_root.rglob(requested.name))
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one SynthEyes exporter matching "
                f"'{exporter_script}', found {len(candidates)}."
            )
        script_path = candidates[0]
        first_line = script_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()[0]
        match = re.match(r"^//SIZZLEX\s+\S+\s+(.+?)\s*$", first_line)
        if not match:
            raise RuntimeError(
                f"'{script_path}' is not a SynthEyes Sizzle exporter."
            )
        return script_path, match.group(1)

    @staticmethod
    def _sizzle_path(path: Path) -> str:
        return str(path).replace("\\", "/").replace('"', '\\"')

    @classmethod
    def _configuration_script(
        cls,
        preset: Path,
        output: Path,
        backup: Path,
        exporter_name: str,
        exporter_script: Path,
    ) -> str:
        return f'''//SIZZLET AYON Configure Export
// Exporter: {exporter_name}
// Script: {cls._sizzle_path(exporter_script)}
fold = WFPreset.FindByFullPathName("/User/Current/Preferences/Folder Preferences")
if (isNull(fold))
    Message("AYON: SynthEyes Folder Preferences were not found.")
else
    fold.SaveToFile("{cls._sizzle_path(backup)}", 1)
    fold.SetValue("Multi-Export Files", "{cls._sizzle_path(output)}")
end
loadResult = WFPreset.AddSource("{cls._sizzle_path(preset)}", "AYONExport")
sceneExporters = WFPreset.current.FindNamedOrCreate("Exporters", "Exporters")
sceneExporters.RemoveAllChildren()
if (loadResult[2] != "")
    Message("AYON: " ++ loadResult[2])
else
    loaded = WFPreset.SourcePreset("AYONExport")
    sourceExporters = loaded
    if (loaded.presetType != "Exporters")
        sourceExporters = loaded.FindByPathName("Current/Exporters")
    end
    if (isNull(sourceExporters))
        Message("AYON: Preset JSON must contain an Exporters preset.")
    elseif (#sourceExporters.child != 1)
        Message("AYON: Preset JSON must contain exactly one export stage.")
    else
        sceneExporters.Duplicate(sourceExporters.child[1], "self")
    end
end
WFPreset.DeleteSource("AYONExport")
'''

    @classmethod
    def _restore_script(cls, backup: Path) -> str:
        return f'''//SIZZLET AYON Restore Export Preferences
fold = WFPreset.FindByFullPathName("/User/Current/Preferences/Folder Preferences")
loadResult = WFPreset.AddSource("{cls._sizzle_path(backup)}", "AYONRestore")
if (loadResult[2] == "")
    saved = WFPreset.SourcePreset("AYONRestore")
    if (saved.ValueIndex("Multi-Export Files") != 0)
        fold.SetValue("Multi-Export Files", saved.Value("Multi-Export Files"))
    else
        fold.DeleteValue("Multi-Export Files")
    end
end
WFPreset.DeleteSource("AYONRestore")
'''
