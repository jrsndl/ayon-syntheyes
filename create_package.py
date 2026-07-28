"""Build an uploadable AYON addon package."""

from __future__ import annotations

import argparse
import io
import os
import shutil
import zipfile
from pathlib import Path

import package

ROOT = Path(__file__).resolve().parent


def _files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.startswith(".")
            and path.suffix != ".pyc"
        ):
            yield path


def _client_zip() -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        client_root = ROOT / "client"
        for path in _files(client_root):
            archive.write(path, path.relative_to(client_root))
        license_path = ROOT / "LICENSE"
        if license_path.exists():
            archive.write(
                license_path,
                Path(package.client_dir) / "LICENSE",
            )
    return stream.getvalue()


def build(output_dir: Path, unpacked: bool = False) -> Path:
    """Create a server package containing zipped private client code."""
    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[Path | bytes, Path]] = [
        (ROOT / "package.py", Path("package.py")),
        (_client_zip(), Path("private/client.zip")),
    ]
    for source_root in ("server", "public", "private"):
        root = ROOT / source_root
        for path in _files(root):
            entries.append((path, path.relative_to(ROOT)))
    if (ROOT / "LICENSE").exists():
        entries.append((ROOT / "LICENSE", Path("LICENSE")))

    if unpacked:
        destination = output_dir / package.name / package.version
        if destination.exists():
            shutil.rmtree(destination)
        for source, relative in entries:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, bytes):
                target.write_bytes(source)
            else:
                shutil.copy2(source, target)
        return destination

    destination = output_dir / f"{package.name}-{package.version}.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, relative in entries:
            if isinstance(source, bytes):
                archive.writestr(str(relative).replace(os.sep, "/"), source)
            else:
                archive.write(source, relative)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "package")
    parser.add_argument("--skip-zip", action="store_true")
    args = parser.parse_args()
    print(build(args.output, args.skip_zip))
