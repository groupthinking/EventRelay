"""Regression tests for the declared Node engine floor.

The root `package.json` advertises the Node versions this repo supports. That
claim is load-bearing in a place that never fails loudly: Vercel reads
`engines.node` to pick the runtime for `apps/web`. `npm install` only *warns*
(`EBADENGINE`) when a package wants a newer Node, so a stale floor never turns a
check red.

Before this test the floor said `>=20.6.0` while every gate in the repo ran on
Node 22 (`ci.yml`, `e2e-tests.yml`, `security.yml`, and `apps/web/Dockerfile`),
and core runtime dependencies — `openai@7`, `ai@7`, the Supabase client — all
declare `>=22`. Node 20 was therefore advertised but never built or tested.

The invariant locked in here is *toolchain consistency*: the version the repo
promises must be the version it actually builds and tests on. Deliberately not
asserted is "the floor dominates every dependency's declared floor" — some dev
tooling (`vitest`, `eslint-visitor-keys`) declares `>=24` and some optional
platform binaries declare `>=22.12`, yet CI passes on Node 22 because those
floors are advisory. Asserting dominance would encode a rule the repo does not
actually follow.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_JSON = REPO_ROOT / "package.json"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
WEB_DOCKERFILE = REPO_ROOT / "apps/web/Dockerfile"

# Workflows whose Node pin defines "the version we actually test on".
CI_WORKFLOWS = (
    REPO_ROOT / ".github/workflows/ci.yml",
    REPO_ROOT / ".github/workflows/e2e-tests.yml",
    REPO_ROOT / ".github/workflows/security.yml",
)

# Direct runtime dependencies whose floor the deployed app must satisfy.
RUNTIME_DEPS_UNDER_TEST = ("openai", "ai", "@ai-sdk/gateway")

_MIN_VERSION = re.compile(r">=\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")
_NODE_VERSION_KEY = re.compile(r"""node-version:\s*['"]?(\d+)""")
_DOCKER_NODE = re.compile(r"^FROM\s+node:(\d+)", re.MULTILINE)


def _parse_floor(spec: str | None) -> tuple[int, int, int] | None:
    """Return the `>=` floor of a semver range as a comparable tuple."""
    if not spec:
        return None
    match = _MIN_VERSION.search(spec)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor or 0), int(patch or 0))


def _load(path: Path) -> dict:
    assert path.exists(), f"{path} should exist"
    return json.loads(path.read_text())


def _declared_floor() -> tuple[int, int, int]:
    engines = _load(PACKAGE_JSON).get("engines") or {}
    floor = _parse_floor(engines.get("node"))
    assert (
        floor is not None
    ), "root package.json must declare engines.node as a >= range"
    return floor


def _locked_floor(name: str) -> tuple[int, int, int] | None:
    """Strictest declared Node floor for any copy of `name` in the lockfile."""
    strictest: tuple[int, int, int] | None = None
    for path, meta in (_load(PACKAGE_LOCK).get("packages") or {}).items():
        if not path or not isinstance(meta, dict):
            continue
        if path.split("node_modules/")[-1] != name:
            continue
        floor = _parse_floor((meta.get("engines") or {}).get("node"))
        if floor is not None and (strictest is None or floor > strictest):
            strictest = floor
    return strictest


def test_declared_floor_matches_the_version_ci_tests_on() -> None:
    """The advertised major must be the major every CI workflow pins."""
    declared_major = _declared_floor()[0]
    for workflow in CI_WORKFLOWS:
        assert workflow.exists(), f"{workflow} should exist"
        pinned = {int(m) for m in _NODE_VERSION_KEY.findall(workflow.read_text())}
        assert pinned, f"{workflow.name} should pin a node-version"
        assert pinned == {declared_major}, (
            f"{workflow.name} tests on Node {sorted(pinned)} but package.json "
            f"advertises >={declared_major}. The repo must promise what it tests."
        )


def test_declared_floor_matches_the_version_the_image_ships() -> None:
    """The advertised major must be the major the production image is built on."""
    assert WEB_DOCKERFILE.exists(), f"{WEB_DOCKERFILE} should exist"
    tags = {int(m) for m in _DOCKER_NODE.findall(WEB_DOCKERFILE.read_text())}
    assert tags, "apps/web/Dockerfile should build FROM a pinned node: tag"
    declared_major = _declared_floor()[0]
    assert tags == {declared_major}, (
        f"apps/web/Dockerfile ships Node {sorted(tags)} but package.json "
        f"advertises >={declared_major}."
    )


@pytest.mark.parametrize("dependency", RUNTIME_DEPS_UNDER_TEST)
def test_declared_floor_satisfies_core_runtime_dependencies(dependency: str) -> None:
    """A runtime dep must never demand a newer Node than Vercel is told to use."""
    required = _locked_floor(dependency)
    assert required is not None, (
        f"expected {dependency} to declare engines.node in package-lock.json; "
        "the fixture has drifted and this test would otherwise be vacuous"
    )
    declared = _declared_floor()
    assert declared >= required, (
        f"{dependency} requires Node >={'.'.join(map(str, required))} but "
        f"package.json advertises >={'.'.join(map(str, declared))}, so Vercel "
        "may select a runtime the dependency does not support"
    )


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (">=22.0.0", (22, 0, 0)),
        (">=22", (22, 0, 0)),
        (">= 20.6.0", (20, 6, 0)),
        ("^20.0.0", None),
        (None, None),
    ],
)
def test_parse_floor(spec: str | None, expected: tuple[int, int, int] | None) -> None:
    assert _parse_floor(spec) == expected
