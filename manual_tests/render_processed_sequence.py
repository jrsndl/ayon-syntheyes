"""Manually render an Image Preprocessor sequence through SynthEyes SyPy.

Run this from SynthEyes with Script > Run Script. Progress and errors are
reported with native Windows message boxes because SynthEyes hides stdout.
"""

import ctypes
import glob
import os
import sys
import tempfile
import time
import traceback
import uuid


SYPY_PARENT = r"C:\Program Files\BorisFX\SynthEyes 2026"
OUTPUT_DIRECTORY = os.path.join(
    tempfile.gettempdir(), "syntheyes_processed_test"
)
FIRST_FRAME = 1001
FILE_EXTENSION = "jpg"
RESET_FILTERING_COLOR = True
RGB_INCLUDED = True
ALPHA_INCLUDED = False
MESHES_INCLUDED = False
FRAME_TIME_BURNIN = False
STABLE_SECONDS = 5.0
RENDER_TIMEOUT_SECONDS = 1200.0


def popup(message, title="SynthEyes processed-sequence test"):
    ctypes.windll.user32.MessageBoxW(0, str(message), title, 0x00000040)


def process_arguments():
    get_command_line = ctypes.windll.kernel32.GetCommandLineW
    get_command_line.restype = ctypes.c_wchar_p
    argc = ctypes.c_int()
    command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
    command_line_to_argv.argtypes = [
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    command_line_to_argv.restype = ctypes.POINTER(ctypes.c_wchar_p)
    argv = command_line_to_argv(get_command_line(), ctypes.byref(argc))
    try:
        return [argv[index] for index in range(argc.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


def argument_value(arguments, flag, default):
    try:
        return arguments[arguments.index(flag) + 1]
    except (ValueError, IndexError):
        return default


def sizzle_path(value):
    return value.replace("\\", "/").replace('"', '\\"')


def write_sizzle_scripts(directory, original_name, defaults_name):
    prepare_path = os.path.join(directory, "prepare_processed_render.szl")
    restore_path = os.path.join(directory, "restore_processed_render.szl")
    prepare = '''//SIZZLET Manual Prepare Processed Plate
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
'''.format(original_name=original_name, defaults_name=defaults_name)
    restore = '''//SIZZLET Manual Restore Processed Plate
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
'''.format(original_name=original_name, defaults_name=defaults_name)
    with open(prepare_path, "w", encoding="utf-8") as stream:
        stream.write(prepare)
    with open(restore_path, "w", encoding="utf-8") as stream:
        stream.write(restore)
    return prepare_path, restore_path


def wait_for_finished_sequence(last_path, pattern, expected_count):
    """Wait without making any SyPy calls while SynthEyes is rendering."""
    deadline = time.monotonic() + RENDER_TIMEOUT_SECONDS
    last_size = -1
    stable_since = None
    observed_count = 0
    while time.monotonic() < deadline:
        observed_count = len(glob.glob(pattern))
        try:
            size = os.path.getsize(last_path)
        except OSError:
            size = -1

        if size > 0 and size == last_size and observed_count >= expected_count:
            if stable_since is None:
                stable_since = time.monotonic()
            elif time.monotonic() - stable_since >= STABLE_SECONDS:
                return observed_count, size
        else:
            stable_since = None
        last_size = size
        time.sleep(0.5)

    raise RuntimeError(
        "Timed out waiting for the processed sequence.\n"
        f"Expected frames: {expected_count}\n"
        f"Observed frames: {observed_count}\n"
        f"Expected final file: {last_path}\n"
        f"Last observed size: {last_size} bytes"
    )


try:
    popup("Python script started. Click OK to connect through SyPy.")

    if SYPY_PARENT not in sys.path:
        sys.path.insert(0, SYPY_PARENT)
    import SyPy3

    arguments = process_arguments()
    port = int(argument_value(arguments, "-l", "0"))
    pin = argument_value(arguments, "-pin", "")
    level = SyPy3.SyLevel()
    if not level.OpenExisting(port, pin):
        raise RuntimeError(
            "Could not connect to the running SynthEyes instance.\n"
            f"Port: {port or '<SyPy default>'}\n"
            f"PIN supplied: {'yes' if pin else 'no'}"
        )

    active = level.Active()
    shot = active.Get("cam").Get("shot")
    scene = level.Scene()
    actual_length = int(shot.Get("actualLength"))
    if actual_length < 1:
        raise RuntimeError("The active shot has no readable frames.")

    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    basename = "syntheyes_processed_test"
    first_path = os.path.join(
        OUTPUT_DIRECTORY,
        f"{basename}.{FIRST_FRAME:04d}.{FILE_EXTENSION}",
    )
    last_frame = FIRST_FRAME + actual_length - 1
    last_path = os.path.join(
        OUTPUT_DIRECTORY,
        f"{basename}.{last_frame:04d}.{FILE_EXTENSION}",
    )
    pattern = os.path.join(
        OUTPUT_DIRECTORY, f"{basename}.*.{FILE_EXTENSION}"
    )
    for old_path in glob.glob(pattern):
        os.remove(old_path)

    previous = {
        "renderFile": shot.Get("renderFile"),
        "renderSettings": shot.Get("renderSettings"),
        "burnInWhen": scene.Get("burnInWhen"),
    }
    token = uuid.uuid4().hex[:16]
    original_name = f"MANUAL_original_{token}"
    defaults_name = f"MANUAL_defaults_{token}"
    temp_directory = tempfile.mkdtemp(prefix="syntheyes_processed_script_")
    prepare_path, restore_path = write_sizzle_scripts(
        temp_directory, original_name, defaults_name
    )
    image_preprocessor_changed = False
    render_popup = None

    popup(
        "Ready to configure the processed render.\n\n"
        f"Output first frame: {first_path}\n"
        f"Expected final frame: {last_path}\n"
        f"Expected frame count: {actual_length}\n"
        f"Reset Filtering/Color: {RESET_FILTERING_COLOR}\n\n"
        "Click OK to continue."
    )

    try:
        if RESET_FILTERING_COLOR:
            level.RunScriptFile(sizzle_path(prepare_path))
            image_preprocessor_changed = True
            popup(
                "Filtering/Color reset completed.\n\n"
                "Click OK to configure Save Sequence."
            )

        level.Begin()
        try:
            shot.Set("renderFile", first_path)
            burn_when = int(previous["burnInWhen"])
            if FRAME_TIME_BURNIN:
                burn_when |= 8
            else:
                burn_when &= ~8
            scene.Set("burnInWhen", burn_when)
        except BaseException:
            level.Cancel()
            raise
        else:
            level.Accept("Configure manual processed render")

        level.PerformActionByNameAndContinue("Save Sequence")
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            render_popup = level.Popup()
            if (
                render_popup.IsValid()
                and render_popup.Name() == "Save Processed Image Sequence"
            ):
                break
            time.sleep(0.05)
        if (
            render_popup is None
            or not render_popup.IsValid()
            or render_popup.Name() != "Save Processed Image Sequence"
        ):
            raise RuntimeError(
                "SynthEyes did not open Save Processed Image Sequence."
            )

        checks = {
            1346: RGB_INCLUDED,
            1570: ALPHA_INCLUDED,
            2250: MESHES_INCLUDED,
            2352: FRAME_TIME_BURNIN,
        }
        for control_id, value in checks.items():
            control = render_popup.ByID(control_id)
            if not control.IsValid():
                raise RuntimeError(
                    f"Save Sequence control {control_id} is unavailable."
                )
            control.SetChecked(int(value))

        start = render_popup.ByID(1)
        if not start.IsValid():
            raise RuntimeError("Save Sequence Start button is unavailable.")

        popup(
            "Save Sequence is configured.\n\n"
            "Click OK to start rendering. The script will not communicate "
            "with SynthEyes until the final image is complete."
        )
        start.ClickAndContinue()
        rendered_count, final_size = wait_for_finished_sequence(
            last_path, pattern, actual_length
        )

        popup(
            "The final image is present and stable.\n\n"
            f"Frames found: {rendered_count}\n"
            f"Final image size: {final_size} bytes\n\n"
            "Click OK to close the render dialog and restore settings."
        )
    finally:
        if render_popup is not None and render_popup.IsValid():
            close = render_popup.ByID(2)
            if close.IsValid():
                close.ClickAndWait()

        if image_preprocessor_changed:
            level.RunScriptFile(sizzle_path(restore_path))

        level.Begin()
        try:
            shot.Set("renderFile", previous["renderFile"])
            shot.Set("renderSettings", previous["renderSettings"])
            scene.Set("burnInWhen", previous["burnInWhen"])
        except BaseException:
            level.Cancel()
            raise
        else:
            level.Accept("Restore manual processed render")

    popup(
        "Processed sequence completed successfully.\n\n"
        f"Output directory: {OUTPUT_DIRECTORY}"
    )
except BaseException:
    popup(
        traceback.format_exc(),
        "SynthEyes processed-sequence test - ERROR",
    )
