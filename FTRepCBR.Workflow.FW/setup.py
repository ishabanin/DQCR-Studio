from __future__ import annotations

from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
DATA_SUFFIXES = {".yml", ".yaml", ".j2", ".html"}


def discover_packages() -> list[str]:
    packages = ["FW"]
    for init_file in sorted(SRC_DIR.rglob("__init__.py")):
        relative_dir = init_file.parent.relative_to(SRC_DIR)
        if relative_dir.parts:
            packages.append("FW." + ".".join(relative_dir.parts))
    return packages


def discover_package_data() -> list[str]:
    files: list[str] = []
    for file_path in sorted(SRC_DIR.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.name == "__init__.py":
            continue
        if file_path.suffix not in DATA_SUFFIXES:
            continue
        files.append(str(file_path.relative_to(SRC_DIR)))
    return files


setup(
    packages=discover_packages(),
    package_dir={"FW": "src"},
    package_data={"FW": discover_package_data()},
)
