"""Launch SynthEyes and keep the AYON/SyPy host process alive."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import traceback

from ayon_core import style
from ayon_core.pipeline import install_host
from qtpy import QtCore, QtWidgets

from ayon_syntheyes.api.connection import (
    connect,
    create_pin,
    import_sypy,
    reserve_listener_port,
)
from ayon_syntheyes.api.control_panel import SynthEyesControlPanel
from ayon_syntheyes.api.host import SynthEyesHost


def main(launch_args: list[str]) -> int:
    if not launch_args:
        raise RuntimeError("The SynthEyes executable argument is missing.")

    executable = os.path.abspath(launch_args[0])
    sypy = import_sypy(executable)
    port = reserve_listener_port()
    pin = create_pin()
    host_args = [executable, "-l", str(port), "-pin", pin, *launch_args[1:]]

    process = subprocess.Popen(host_args, env=os.environ.copy())
    try:
        timeout = float(os.getenv("AYON_SYNTHEYES_CONNECT_TIMEOUT", "60"))
        level = connect(sypy, port, pin, timeout)
    except Exception:
        process.terminate()
        raise

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(style.load_stylesheet())
    host = SynthEyesHost(level)
    install_host(host)
    panel = SynthEyesControlPanel()
    host.set_main_window(panel)
    panel.show()

    timer = QtCore.QTimer()
    timer.setInterval(500)
    timer.timeout.connect(
        lambda: app.quit() if process.poll() is not None else None
    )
    timer.start()

    def stop(*_args: object) -> None:
        if process.poll() is None:
            process.terminate()
        app.quit()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    return app.exec_()


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception:
        traceback.print_exc()
        raise
