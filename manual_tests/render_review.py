"""Manually render a SynthEyes Perspective review through SyPy."""

import ctypes
import os
import sys
import tempfile
import time
import traceback


SYPY_PARENT = r"C:\Program Files\BorisFX\SynthEyes 2026"
OUTPUT_FILE = os.path.join(tempfile.gettempdir(), "syntheyes_review_test.mov")

# Supported values include None, Low, Medium, High, Moblur Low,
# Moblur Medium, and Moblur High. Keep None as the safe default.
ANTI_ALIASING_MOTION_BLUR = "None"
MINIMUM_MOVIE_SIZE = 4096
STABLE_SECONDS = 5.0
RENDER_TIMEOUT_SECONDS = 300.0


def popup(message, title="SynthEyes manual review test"):
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


def is_finalized_mov(path):
    """Return whether a complete MOV atom table including moov exists."""
    try:
        file_size = os.path.getsize(path)
        with open(path, "rb") as stream:
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
                if atom_size < header_size or offset + atom_size > file_size:
                    return False
                found_moov = found_moov or atom_type == b"moov"
                offset += atom_size
            return found_moov and offset == file_size
    except OSError:
        return False


def wait_for_finished_movie(path):
    """Wait without sending SyPy commands while SynthEyes is encoding."""
    deadline = time.monotonic() + RENDER_TIMEOUT_SECONDS
    last_size = -1
    stable_since = None
    while time.monotonic() < deadline:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1

        if (
            size >= MINIMUM_MOVIE_SIZE
            and size == last_size
            and is_finalized_mov(path)
        ):
            if stable_since is None:
                stable_since = time.monotonic()
            elif time.monotonic() - stable_since >= STABLE_SECONDS:
                return size
        else:
            stable_since = None
        last_size = size
        time.sleep(0.5)

    raise RuntimeError(
        "Timed out waiting for SynthEyes to finalize the review.\n"
        f"Last observed size: {last_size} bytes\n"
        f"Output: {path}"
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
    actual_length = int(shot.Get("actualLength"))
    if actual_length < 1:
        raise RuntimeError("The active shot has no readable frames.")

    previous = {
        "previewFile": shot.Get("previewFile"),
        "frameCount": shot.Get("frameCount"),
        "start": shot.Get("start"),
        "stop": shot.Get("stop"),
        "animStart": level.AnimStart(),
        "animEnd": level.AnimEnd(),
        "view": level.View(),
    }
    render_start = 0
    render_end = actual_length - 1

    popup(
        "Ready to render.\n\n"
        f"Output: {OUTPUT_FILE}\n"
        f"Reader frames: {actual_length}\n"
        f"Internal range: {render_start}-{render_end}\n"
        f"AA / motion blur: {ANTI_ALIASING_MOTION_BLUR}"
    )

    if os.path.isfile(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    level.BeginShotChanges(shot)
    try:
        shot.Set("previewFile", OUTPUT_FILE)
        shot.Set("frameCount", actual_length)
        shot.Set("start", render_start)
        shot.Set("stop", render_end)
    except BaseException:
        level.Cancel()
        raise
    else:
        level.AcceptShotChanges(shot, "Configure manual review test")

    level.SetAnimStart(render_start)
    level.SetAnimEnd(render_end)
    review_popup = None
    try:
        level.SetView("Perspective")
        perspective = level.Main().ByClass("Perspect")
        if not perspective.IsValid():
            raise RuntimeError("The Perspective viewport is unavailable.")

        perspective.PerformActionByNameAndContinue("Persp/Preview Movie")
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            review_popup = level.Popup()
            if (
                review_popup.IsValid()
                and review_popup.Name() == "Preview Movie Settings"
            ):
                break
            time.sleep(0.05)
        if (
            review_popup is None
            or not review_popup.IsValid()
            or review_popup.Name() != "Preview Movie Settings"
        ):
            raise RuntimeError("Preview Movie Settings did not open.")

        quality = review_popup.ByID(1339)
        if not quality.IsValid():
            raise RuntimeError("AA / motion-blur selector was not found.")
        quality.SetOption(ANTI_ALIASING_MOTION_BLUR)

        start_button = review_popup.ByID(1)
        if not start_button.IsValid():
            raise RuntimeError("Preview Movie Start button was not found.")

        popup("Click OK to press Start and render the review.")
        start_button.ClickAndContinue()
        rendered_size = wait_for_finished_movie(OUTPUT_FILE)
    finally:
        if review_popup is not None and review_popup.IsValid():
            cancel = review_popup.ByID(2)
            if cancel.IsValid():
                cancel.ClickAndWait()
        level.SetView(previous["view"])
        level.SetAnimStart(previous["animStart"])
        level.SetAnimEnd(previous["animEnd"])
        level.BeginShotChanges(shot)
        try:
            shot.Set("previewFile", previous["previewFile"])
            shot.Set("frameCount", previous["frameCount"])
            shot.Set("start", previous["start"])
            shot.Set("stop", previous["stop"])
        except BaseException:
            level.Cancel()
            raise
        else:
            level.AcceptShotChanges(shot, "Restore manual review test")

    popup(
        "Review completed successfully.\n\n"
        f"Output: {OUTPUT_FILE}\n"
        f"Size: {rendered_size} bytes"
    )
except BaseException:
    popup(
        traceback.format_exc(),
        "SynthEyes manual review test - ERROR",
    )
