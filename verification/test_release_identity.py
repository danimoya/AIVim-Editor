"""Alpha identities must agree across Git tags, Python and the browser package."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "aivim_release_version", ROOT / "scripts/bump_version.py"
)
versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(versions)


def test_prerelease_tag_mapping():
    assert versions.tag_for("1.0.0a1") == "v1.0.0-alpha.1"
    assert versions.tag_for("1.0.0b2") == "v1.0.0-beta.2"
    assert versions.tag_for("1.0.0rc3") == "v1.0.0-rc.3"
    assert versions.tag_for("1.0.0") == "v1.0.0"


def test_committed_release_mirrors():
    value = versions.version()
    assert (ROOT / "VERSION").read_text().strip() == value
    package = json.loads((ROOT / "package.json").read_text())
    lock = json.loads((ROOT / "package-lock.json").read_text())
    assert (
        package["version"]
        == lock["version"]
        == lock["packages"][""]["version"]
        == versions.tag_for(value)[1:]
    )
