#!/usr/bin/env python3
"""Create an unsigned XPI from a WebExtension source directory."""
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

EXCLUDED_DIRS = {".git", ".github", "node_modules", "__pycache__", "tests", "test"}
EXCLUDED_NAMES = {".DS_Store", ".gitignore", ".gitattributes"}

def package(source: Path, output: Path):
    manifest = source / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["manifest_version"] in (2, 3)
    assert data["browser_specific_settings"]["gecko"]["id"].endswith("@dreadaxe")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.name.endswith((".orig", ".pyc")):
            continue
        files.append((path, rel.as_posix()))
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=8) as archive:
        for path, name in files:
            archive.write(path, name)
    with ZipFile(output) as archive:
        assert "manifest.json" in archive.namelist()
        assert len(archive.namelist()) > 10, "Archive unexpectedly empty"
    print(f"Unsigned test archive: {output} ({len(files)} files)")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: package_xpi.py SOURCE_DIR OUTPUT.xpi")
    package(Path(sys.argv[1]), Path(sys.argv[2]))
