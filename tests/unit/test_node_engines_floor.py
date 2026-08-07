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
promises must be the version it actually builds and tests on.

Deliberately not asserted is "the floor dominates every dependency's declared
floor". Much of the tree uses *union* ranges — `vitest@4.1.10` is
`^20.0.0 || ^22.0.0 || >=24.0.0`, `eslint-visitor-keys@5.0.1` is
`^20.19.0 || ^22.13.0 || >=24` — whose trailing `>=` branch is one alternative
among several, not an unconditional minimum. Both explicitly admit Node 22.
Reading such a range as "requires >=24" is simply wrong, so `_parse_floor`
below refuses to guess: it accepts only a range that is a single, complete
`>=` clause and returns `None` for every other form. A selected runtime
dependency that adopts an unsupported form fails loudly rather than silently
contributing a fabricated floor.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

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

# Anchored: the whole range must be one `>=` clause. An unanchored search would
# happily pull `>=24.0.0` out of `^20.0.0 || ^22.0.0 || >=24.0.0` and report a
# floor of 24 for a range that accepts Node 20.
_MIN_VERSION = re.compile(r"^>=\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_DOCKER_NODE = re.compile(r"^FROM\s+node:(\d+)", re.MULTILINE)


def _walk(node: Any) -> Iterator[Any]:
    """Yield every mapping nested anywhere inside a parsed YAML document."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _pinned_node_majors(workflow: Path) -> set[int]:
    """Every Node major a workflow pins via `actions/setup-node`.

    Parsed rather than text-matched so a commented-out or documentation-only
    `node-version:` line cannot fail this test spuriously.
    """
    document = yaml.safe_load(workflow.read_text())
    majors: set[int] = set()
    for mapping in _walk(document):
        pin = (mapping.get("with") or {}).get("node-version") if mapping else None
        if pin is None:
            continue
        match = re.match(r"v?(\d+)", str(pin).strip())
        if match:
            majors.add(int(match.group(1)))
    return majors


def _parse_floor(spec: str | None) -> tuple[int, int, int] | None:
    """Return the floor of a semver range, or `None` if it is not a bare `>=`.

    Only a range that is *entirely* one `>=X[.Y[.Z]]` clause has an unambiguous
    minimum. Unions (`a || b`) and compound ranges (`>=22 <24`) return `None`
    rather than a guess — see the module docstring.
    """
    if not spec:
        return None
    match = _MIN_VERSION.match(spec.strip())
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
        pinned = _pinned_node_majors(workflow)
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
        f"expected {dependency} to declare engines.node in package-lock.json as "
        "a bare '>=' range. Either it is now absent, or it moved to a union or "
        "compound range that _parse_floor deliberately refuses to reduce to a "
        "single floor. Re-read the range by hand and either widen the parser or "
        "drop this dependency from RUNTIME_DEPS_UNDER_TEST — do not let the "
        "check pass vacuously."
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
        ("  >=22.0.0  ", (22, 0, 0)),
        ("v22.0.0", None),
        ("^20.0.0", None),
        ("", None),
        (None, None),
        # Union ranges have no single minimum: the trailing `>=` branch is one
        # alternative, not a floor. These are the real ranges carried by
        # vitest@4.1.10, eslint-visitor-keys@5.0.1, chrome-devtools-mcp@1.6.0
        # and vite@8.2.0 — every one of them admits Node 22, so reading the
        # last branch as a requirement would be actively wrong.
        ("^20.0.0 || ^22.0.0 || >=24.0.0", None),
        ("^20.19.0 || ^22.13.0 || >=24", None),
        ("^20.19.0 || >=22.12.0", None),
        (">=22.0.0 || >=24.0.0", None),
        # Compound ranges are bounded above, so `>=` alone does not describe them.
        (">=22.0.0 <24.0.0", None),
    ],
)
def test_parse_floor(spec: str | None, expected: tuple[int, int, int] | None) -> None:
    assert _parse_floor(spec) == expected


def test_pinned_node_majors_ignores_commented_and_unrelated_keys(
    tmp_path: Path,
) -> None:
    """A `node-version` outside a `with:` block must not be read as a pin."""
    workflow = tmp_path / "sample.yml"
    workflow.write_text(
        "jobs:\n"
        "  build:\n"
        "    steps:\n"
        "      - uses: actions/setup-node@v4\n"
        '        with:\n          node-version: "22"\n'
        "      # node-version: 18   <- a comment must be ignored\n"
        "      - name: not a setup step\n"
        "        env:\n          NOTE: node-version 16 mentioned in prose\n"
    )
    assert _pinned_node_majors(workflow) == {22}
