"""Diagnose which AYON post-load setting causes SynthEyes to fail."""

import ctypes
import sys
import traceback

SYPY_PARENT = r"C:\Program Files\BorisFX\SynthEyes 2026"
FIRST_FRAME = (
    r"Z:\BCV_000_Playground\shots\010\mshot_010_080\publish\plate"
    r"\platePl01\v001\mshot_010_080_platePl01_v001.1001.exr"
)


def popup(message, title="SynthEyes configured sequence test"):
    ctypes.windll.user32.MessageBoxW(0, str(message), title, 0x00000040)


def process_arguments():
    """Return the actual SynthEyes process arguments on Windows."""
    get_command_line = ctypes.windll.kernel32.GetCommandLineW
    get_command_line.restype = ctypes.c_wchar_p
    argc = ctypes.c_int()
    command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
    command_line_to_argv.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
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


def apply_shot_change(level, shot, label, change):
    popup(f"NEXT: {label}\n\nClick OK to apply this change.")
    level.BeginShotChanges(shot)
    try:
        change()
    except BaseException:
        level.Cancel()
        raise
    else:
        level.AcceptShotChanges(shot, f"Test {label}")
    popup(f"COMPLETED: {label}")


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

    popup(
        "Connected. Click OK to call NewSceneAndShot.\n\n"
        "This replaces the current SynthEyes scene.\n\n"
        f"First frame:\n{FIRST_FRAME}"
    )

    previous_workfile = level.SNIFileName() or ""
    previous_info = level.Scene().Get("info") or ""
    shot = level.NewSceneAndShot(FIRST_FRAME, 0.0)
    if shot is None:
        raise RuntimeError("SynthEyes NewSceneAndShot returned None.")

    popup(
        "BASE LOAD SUCCEEDED.\n\n"
        f"Shot name: {shot.Name()}\n"
        f"Reader type: {shot.Get('readerType')}\n"
        f"First file: {shot.Get('nm')}\n"
        f"Frames: {shot.Get('actualLength')}"
    )

    if previous_workfile:
        popup("NEXT: restore the previous SNI filename.")
        level.SetSNIFileName(previous_workfile)
        popup("COMPLETED: restore the previous SNI filename.")

    apply_shot_change(
        level, shot, "match frame numbers", lambda: shot.Set("matchFrameNumbers", 1)
    )
    apply_shot_change(level, shot, "24 fps", lambda: shot.Set("rate", 24.0))
    apply_shot_change(
        level, shot, "process depth Half", lambda: shot.Set("processFormat", 2)
    )
    apply_shot_change(
        level, shot, "output depth Half", lambda: shot.Set("storeFormat", 2)
    )

    live = shot.Get("live")
    apply_shot_change(level, shot, "VR mode None", lambda: live.Set("vrmode", 0))
    apply_shot_change(level, shot, "3D LUT None", lambda: live.Set("colormapName", ""))
    apply_shot_change(
        level,
        shot,
        "levels Low/Mid/High = 0/0.5/1",
        lambda: live.Set("levels", [0.0, 0.5, 1.0]),
    )

    if previous_info:
        popup("NEXT: restore the previous Scene Information description.")
        level.Begin()
        try:
            level.Scene().Set("info", previous_info)
        except BaseException:
            level.Cancel()
            raise
        else:
            level.Accept("Test restore Scene Information")
        popup("COMPLETED: restore the previous Scene Information description.")

    popup("ALL ADDON POST-LOAD OPERATIONS COMPLETED SUCCESSFULLY.")
except BaseException:
    popup(
        f"SyPy parent directory:\n{SYPY_PARENT}\n\n{traceback.format_exc()}",
        "SynthEyes SyPy sequence test - ERROR",
    )
