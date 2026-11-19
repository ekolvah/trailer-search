"""Every version place agrees with the release-please manifest (spec: release)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "x-release-please-version"


def lagging_places(manifest: str, places: dict[str, str | None]) -> list[str]:
    """Names each place whose version differs from the manifest's."""
    return [
        f"{name}: {version} != {manifest}"
        for name, version in places.items()
        if version != manifest
    ]


def _readme_version() -> str | None:
    for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines():
        if MARKER in line:
            found = re.search(r"@v(\d+\.\d+\.\d+)", line)
            return found.group(1) if found else None
    return None


def test_version_places_match_manifest() -> None:
    manifest = json.loads(
        (ROOT / ".release-please-manifest.json").read_text(encoding="utf-8")
    )["."]
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    assert (
        lagging_places(
            manifest, {"pyproject.toml": pyproject, "README.md": _readme_version()}
        )
        == []
    )


def test_lagging_place_named() -> None:
    assert lagging_places(
        "0.2.1", {"pyproject.toml": "0.2.1", "README.md": "0.2.0"}
    ) == ["README.md: 0.2.0 != 0.2.1"]
