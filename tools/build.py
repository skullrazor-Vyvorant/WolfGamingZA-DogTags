#!/usr/bin/env python3
"""Build an unsigned, uncompressed DayZ development PBO using Python's stdlib.

This packages source. It does not compile Enforce Script or validate DayZ assets.
PBO header/checksum layout follows the public armake2 PBO format implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path, PureWindowsPath
import re
import struct
import zipfile


HEADER = struct.Struct("<5I")
VERSION = 0x56657273
PREFIX = "WGZA_DogTags"
MOD = "@WGZA_DogTags"
RUNTIME_SUFFIXES = {".c", ".cpp", ".layout", ".paa", ".p3d", ".rvmat", ".xml", ".csv", ".ogg", ".imageset"}


def cstring(value: str) -> bytes:
    if "\x00" in value:
        raise ValueError("NUL in PBO string")
    return value.encode("ascii") + b"\x00"


def runtime_files(source: Path) -> dict[str, bytes]:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Source must be a real directory, not a symlink")
    prefix_path = source / "$PBOPREFIX$"
    if prefix_path.is_symlink():
        raise ValueError("Symlinked prefix is not allowed")
    if prefix_path.read_text(encoding="ascii").strip() != PREFIX:
        raise ValueError(f"Expected PBO prefix {PREFIX}")
    files: dict[str, bytes] = {}
    seen: set[str] = set()
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks cannot enter a build: {path}")
        if not path.is_file() or path == prefix_path:
            continue
        relative = path.relative_to(source)
        if any(part.startswith(".") for part in relative.parts) or path.suffix.lower() not in RUNTIME_SUFFIXES:
            raise ValueError(f"Unexpected runtime file (move outside addon source): {relative}")
        name = "\\".join(relative.parts)
        # PBO virtual paths are Windows paths, including on the Linux build host.
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in relative.parts):
            raise ValueError(f"Unsupported runtime path: {relative}")
        if name.casefold() in seen:
            raise ValueError(f"Case-insensitive filename collision: {name}")
        seen.add(name.casefold())
        files[name] = path.read_bytes()
    if "config.cpp" not in files:
        raise ValueError("Missing config.cpp")
    for module in ("4_World", "5_Mission"):
        if not any(name.startswith(f"scripts\\{module}\\") and name.endswith(".c") for name in files):
            raise ValueError(f"No source in {module}")
    return dict(sorted(files.items(), key=lambda item: item[0].casefold()))


def pack_pbo(source: Path) -> bytes:
    files = runtime_files(source)
    headers = bytearray(cstring("") + HEADER.pack(VERSION, 0, 0, 0, 0))
    headers += cstring("prefix") + cstring(PREFIX) + cstring("")
    for name, data in files.items():
        headers += cstring(name) + HEADER.pack(0, len(data), 0, 0, len(data))
    headers += cstring("") + HEADER.pack(0, 0, 0, 0, 0)
    contents = bytes(headers) + b"".join(files.values())
    # The 21-byte footer is not included in the PBO checksum.
    return contents + b"\x00" + hashlib.sha1(contents).digest()


def verify_pbo(data: bytes) -> dict[str, bytes]:
    """Validate structure, byte coverage, prefix, filenames and footer checksum."""
    if len(data) < 42 or data[-21] != 0 or hashlib.sha1(data[:-21]).digest() != data[-20:]:
        raise ValueError("Invalid PBO checksum/footer")
    stream = io.BytesIO(data[:-21])

    def read_string() -> str:
        result = bytearray()
        while True:
            char = stream.read(1)
            if not char:
                raise ValueError("Unterminated PBO string")
            if char == b"\x00":
                return result.decode("ascii")
            result += char

    def read_header() -> tuple[int, ...]:
        fields = stream.read(HEADER.size)
        if len(fields) != HEADER.size:
            raise ValueError("Truncated PBO header")
        return HEADER.unpack(fields)

    if read_string() != "" or read_header() != (VERSION, 0, 0, 0, 0):
        raise ValueError("Missing PBO version header")
    if read_string() != "prefix" or read_string() != PREFIX or read_string() != "":
        raise ValueError("Wrong PBO prefix")
    headers: list[tuple[str, int]] = []
    seen: set[str] = set()
    while True:
        name = read_string()
        method, original, reserved, timestamp, size = read_header()
        if not name:
            if any((method, original, reserved, timestamp, size)):
                raise ValueError("Invalid PBO end marker")
            break
        path = PureWindowsPath(name)
        if path.is_absolute() or path.drive or ".." in path.parts or "/" in name or name.casefold() in seen:
            raise ValueError("Invalid or duplicate PBO filename")
        if method != 0 or original != size or reserved != 0 or timestamp != 0:
            raise ValueError("Unsupported PBO entry")
        seen.add(name.casefold())
        headers.append((name, size))
    files = {}
    for name, size in headers:
        payload = stream.read(size)
        if len(payload) != size:
            raise ValueError("Truncated PBO payload")
        files[name] = payload
    if stream.read(1):
        raise ValueError("Unexpected bytes after PBO payload")
    if not files:
        raise ValueError("Empty PBO")
    return files


def build(repository: Path, output: Path) -> Path:
    repository = repository.resolve()
    output = output.resolve()
    source = repository / PREFIX
    if output == repository or output == source or source in output.parents:
        raise ValueError("Build output must be outside the addon source and not the repository root")
    pbo = pack_pbo(source)
    if verify_pbo(pbo) != runtime_files(source):
        raise ValueError("PBO verification did not recover the complete addon source")
    payloads = {
        f"{MOD}/Addons/{PREFIX}.pbo": pbo,
        f"{MOD}/mod.cpp": (repository / "packaging/mod.cpp").read_bytes(),
        f"{MOD}/TESTING.md": (repository / "docs/TESTING.md").read_bytes(),
        f"{MOD}/server/README.md": (repository / "server/README.md").read_bytes(),
        f"{MOD}/server/types_WGZA_DogTags.xml": (repository / "server/types_WGZA_DogTags.xml").read_bytes(),
    }
    checksum_lines = [f"{hashlib.sha256(data).hexdigest()}  {name.removeprefix(MOD + '/')}\n" for name, data in sorted(payloads.items())]
    payloads[f"{MOD}/SHA256SUMS"] = "".join(checksum_lines).encode("ascii")
    # Do not merge with an old mod folder or follow output symlinks. Only emit a ZIP.
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "WGZA_DogTags-dev.zip"
    if destination.is_symlink():
        raise ValueError("Refusing to overwrite symlinked ZIP")
    temporary = output / "WGZA_DogTags-dev.zip.tmp"
    if temporary.is_symlink():
        raise ValueError("Refusing to overwrite symlinked temporary ZIP")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, data)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
    temporary.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Output directory (default: repository/dist)")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    try:
        destination = build(repository, args.output or repository / "dist")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(f"Unsigned source development build: {destination}")
    print(f"SHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")
    print("Packaging verified. Enforce Script and gameplay still require DayZ validation.")


if __name__ == "__main__":
    main()
