"""Minimal SynthEyes SyPy test for opening an EXR image sequence."""

import ctypes
import sys
import traceback

SYPY_PARENT = r"C:\Program Files\BorisFX\SynthEyes 2026"
FIRST_FRAME = (
    r"Z:\BCV_000_Playground\shots\010\mshot_010_080\publish\plate"
    r"\platePl01\v001\mshot_010_080_platePl01_v001.1001.exr"
)


def popup(message, title="SynthEyes SyPy sequence test"):
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

    shot = level.NewSceneAndShot(FIRST_FRAME, 0.0)
    if shot is None:
        raise RuntimeError("SynthEyes NewSceneAndShot returned None.")

    popup(
        "Sequence loaded successfully.\n\n"
        f"Shot name: {shot.Name()}\n"
        f"Reader type: {shot.Get('readerType')}\n"
        f"First file: {shot.Get('nm')}\n"
        f"Frames: {shot.Get('actualLength')}"
    )
except BaseException:
    popup(
        f"SyPy parent directory:\n{SYPY_PARENT}\n\n{traceback.format_exc()}",
        "SynthEyes SyPy sequence test - ERROR",
    )
