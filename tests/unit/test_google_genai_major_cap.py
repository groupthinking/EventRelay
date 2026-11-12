"""Guard the Python Gemini SDK (google-genai) against an unplanned major upgrade.

google-genai 3.0.0 changed Developer API defaults (v1beta -> v1) and the default
HTTP client (httpx -> httpx2). EventRelay's adapters construct clients without
pinning either, so a fresh unlocked resolve must stay on 2.x until a deliberate
v3 migration lands (see #2637). Today google-cloud-aiplatform also caps
google-genai <3 transitively, but that is Google's constraint, not ours.
"""

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - project requires >=3.11
    import tomli as tomllib

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "google-genai"
FIRST_UNSUPPORTED = Version("3.0.0")


def _assert_capped(spec: str, where: str) -> None:
    req = Requirement(spec)
    assert req.name == PACKAGE, where
    assert not req.specifier.contains(FIRST_UNSUPPORTED, prereleases=True), (
        f"{where}: '{spec}' admits google-genai 3.x; keep '<3' until the v3 "
        "migration is done (#2637)"
    )
    assert not req.specifier.contains("3.0.0rc1", prereleases=True), where


def _declarations_in(lines, where):
    found = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if line and Requirement(line).name == PACKAGE:
            found.append(line)
    assert found, f"{where} no longer declares {PACKAGE}"
    return found


def _lock() -> dict:
    return tomllib.loads((ROOT / "uv.lock").read_text())


def test_pyproject_caps_google_genai_below_3():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    specs = list(project["dependencies"])
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    for spec in _declarations_in(specs, "pyproject.toml"):
        _assert_capped(spec, "pyproject.toml")


def test_requirements_txt_caps_google_genai_below_3():
    text = (ROOT / "requirements.txt").read_text().splitlines()
    lines = [line for line in text if not line.lstrip().startswith("-")]
    for spec in _declarations_in(lines, "requirements.txt"):
        _assert_capped(spec, "requirements.txt")


def test_uv_lock_records_cap_and_resolves_2x():
    packages = _lock()["package"]
    root = next(p for p in packages if p.get("source", {}).get("editable") == ".")
    lock_specs = [
        d for d in root["metadata"]["requires-dist"] if d["name"] == PACKAGE
    ]
    assert lock_specs, "uv.lock root metadata lost google-genai"
    for dep in lock_specs:
        _assert_capped(f"{PACKAGE}{dep['specifier']}", "uv.lock requires-dist")

    locked = [Version(p["version"]) for p in packages if p["name"] == PACKAGE]
    assert locked and all(v.major == 2 for v in locked), locked
