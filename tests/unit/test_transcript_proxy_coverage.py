"""Structural guard: every transcript client must route through the proxy.

``youtube-transcript-api`` >=1.0 only honours a proxy when a ``proxy_config`` is
handed to the constructor. A bare ``YouTubeTranscriptApi()`` silently egresses
from the host's own IP, which both defeats the centralized outbound proxy and
re-exposes the pipeline to YouTube's IP blocking.

Reviewing this by eye does not scale — the constructor is called from 14 sites
across 6 modules. This module walks the AST of every tracked Python file and
fails if any construction omits ``proxy_config``, so a regression is caught at
test time rather than in production.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Directories that ship runtime code. Tests and fixtures are excluded on
#: purpose: a test is allowed to construct a bare client against a stub.
SOURCE_ROOTS = ("src", "shared")

CLIENT_NAME = "YouTubeTranscriptApi"
REQUIRED_KEYWORD = "proxy_config"

#: Canonical helper that resolves the configured proxy (or ``None``).
PROXY_HELPER = "get_transcript_proxy_config"

#: Module that must supply the helper.
PROXY_MODULE = "youtube_extension.utils.proxy"


def _python_files() -> list[Path]:
    # A configured root that has been moved or renamed must be a hard failure.
    # Skipping it silently would shrink the scanned surface while every
    # assertion below still passes against the remaining roots.
    missing = [root for root in SOURCE_ROOTS if not (PROJECT_ROOT / root).is_dir()]
    if missing:
        raise AssertionError(
            "configured source roots are missing: "
            + ", ".join(sorted(missing))
            + " -- the proxy guard would stop scanning them while still "
            "reporting success. Update SOURCE_ROOTS if the layout changed."
        )

    files: list[Path] = []
    for root in SOURCE_ROOTS:
        base = PROJECT_ROOT / root
        for path in base.rglob("*.py"):
            if any(
                part in {"__pycache__", "node_modules", ".venv"} for part in path.parts
            ):
                continue
            files.append(path)
    return sorted(files)


def _client_constructions(tree: ast.AST) -> list[ast.Call]:
    """Return every ``YouTubeTranscriptApi(...)`` call node in ``tree``."""
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Bare name: ``YouTubeTranscriptApi(...)``
        if isinstance(func, ast.Name) and func.id == CLIENT_NAME:
            calls.append(node)
        # Attribute access: ``module.YouTubeTranscriptApi(...)``
        elif isinstance(func, ast.Attribute) and func.attr == CLIENT_NAME:
            calls.append(node)
    return calls


def _has_required_keyword(call: ast.Call) -> bool:
    for keyword in call.keywords:
        # ``proxy_config=...``
        if keyword.arg == REQUIRED_KEYWORD:
            return True
        # ``**kwargs`` — the keyword may be supplied dynamically; treat the
        # call as opaque rather than reporting a false positive.
        if keyword.arg is None:
            return True
    return False


def _collect_unproxied() -> list[str]:
    offenders: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        for call in _client_constructions(tree):
            if not _has_required_keyword(call):
                rel = path.relative_to(PROJECT_ROOT)
                offenders.append(f"{rel}:{call.lineno}")
    return offenders


def test_guard_finds_the_client_at_all() -> None:
    """Fail loudly if the scan matches nothing.

    Without this, a rename of the client (or a broken path constant) would turn
    every other test in this module into a vacuous pass.
    """
    total = 0
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        total += len(_client_constructions(tree))

    assert total >= 10, (
        f"Expected the transcript client to be constructed across the pipeline, "
        f"found {total} call sites. Either {CLIENT_NAME} was renamed or "
        f"SOURCE_ROOTS={SOURCE_ROOTS} no longer resolves — fix the guard before "
        f"trusting the assertions below."
    )


#: Trees that legitimately construct the client without production egress.
EXEMPT_ROOTS = frozenset({"tests"})

#: Directories never worth scanning.
SKIP_DIRS = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "build",
        "dist",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)


def test_source_roots_cover_every_tree_that_builds_the_client() -> None:
    """``SOURCE_ROOTS`` must be derived from reality, not hand-maintained.

    Narrowing the tuple (say, dropping ``shared``) would leave every other
    assertion in this module passing against a smaller surface. Rather than
    trusting the constant, rediscover which trees actually construct the
    client and require the constant to cover them.
    """
    found: dict[str, int] = {}
    unparseable: list[str] = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            unparseable.append(str(path.relative_to(PROJECT_ROOT)))
            continue
        if _client_constructions(tree):
            root = path.relative_to(PROJECT_ROOT).parts[0]
            found[root] = found.get(root, 0) + 1

    assert not unparseable, (
        "these files could not be parsed, so the scan silently skipped them: "
        + ", ".join(sorted(unparseable))
    )

    required = {root for root in found if root not in EXEMPT_ROOTS}
    uncovered = required - set(SOURCE_ROOTS)
    assert not uncovered, (
        f"{sorted(uncovered)} construct {CLIENT_NAME} but are not listed in "
        f"SOURCE_ROOTS={list(SOURCE_ROOTS)}, so the proxy guard does not scan "
        "them. Add them or mark them exempt."
    )


def test_missing_source_root_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A renamed or moved source root must break the guard, not shrink it.

    Without this, dropping ``shared`` from the tree would leave ``src`` alone
    satisfying every assertion in this module and the guard would silently stop
    protecting the shared runtime code.
    """
    monkeypatch.setattr(
        sys.modules[__name__],
        "SOURCE_ROOTS",
        SOURCE_ROOTS + ("definitely_not_a_real_root",),
    )
    with pytest.raises(AssertionError, match="definitely_not_a_real_root"):
        _python_files()


def test_every_transcript_client_passes_proxy_config() -> None:
    """No runtime code may construct the client without ``proxy_config``."""
    offenders = _collect_unproxied()

    assert not offenders, (
        f"{len(offenders)} {CLIENT_NAME}(...) construction(s) omit "
        f"'{REQUIRED_KEYWORD}=' and will bypass the centralized proxy:\n  "
        + "\n  ".join(offenders)
        + f"\n\nPass {REQUIRED_KEYWORD}={PROXY_HELPER}() — it returns None when "
        f"WEBSHARE_PROXY_URL is unset, so direct connections still work."
    )


#: Modules that construct the client outside the ``youtube_extension`` package
#: and therefore need the sys.path bootstrap to reach the canonical helper.
BOOTSTRAPPED_MODULES = (
    "src/integration/youtube_api.py",
    "src/agents/process_video_with_mcp.py",
    "src/agents/interactive_metadata_extractor.py",
    "src/mcp/mcp_video_processor.py",
)


@pytest.mark.parametrize("module_path", BOOTSTRAPPED_MODULES)
def test_module_never_stubs_the_proxy_helper_to_none(module_path: str) -> None:
    """A local fallback returning ``None`` silently disables the proxy.

    ``proxy_config=get_transcript_proxy_config()`` looks correct at the call
    site, so the AST coverage test above still passes -- but if the name
    resolves to a stub that returns ``None`` the client egresses directly from
    the host IP. That is the very failure this module exists to prevent, so the
    stub shape is banned outright.
    """
    path = PROJECT_ROOT / module_path
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != PROXY_HELPER:
            continue
        body = [n for n in node.body if not isinstance(n, ast.Expr)]
        returns_only_none = all(
            isinstance(n, ast.Return)
            and isinstance(n.value, ast.Constant)
            and n.value.value is None
            for n in body
        )
        assert not returns_only_none, (
            f"{module_path} defines a local {PROXY_HELPER}() that returns None. "
            "Bootstrap sys.path to the canonical helper or fail closed; do not "
            "silently bypass the proxy."
        )


@pytest.mark.parametrize("module_path", BOOTSTRAPPED_MODULES)
def test_bootstrap_path_actually_reaches_the_canonical_helper(
    module_path: str,
) -> None:
    """The fallback inserts ``parents[1]``; prove that really is ``src``.

    If a module moves to a different nesting depth the arithmetic silently
    points somewhere useless and the import would fail closed at runtime.
    """
    path = (PROJECT_ROOT / module_path).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    # Read the index the source actually uses instead of assuming it, so that
    # changing ``parents[1]`` in the module is what this test reacts to. Scope
    # the search to the sys.path.insert bootstrap: these modules legitimately
    # use ``parents[N]`` elsewhere for unrelated path maths.
    inserts = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "insert"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "path"
    ]
    assert len(inserts) == 1, (
        f"{module_path}: expected exactly one sys.path.insert bootstrap, "
        f"found {len(inserts)}."
    )

    indices = [
        node.slice.value
        for node in ast.walk(inserts[0])
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "parents"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, int)
    ]
    assert len(indices) == 1, (
        f"{module_path}: expected exactly one ``parents[N]`` index inside the "
        f"sys.path bootstrap, found {indices}."
    )

    bootstrapped_root = path.parents[indices[0]]
    helper = bootstrapped_root / "youtube_extension" / "utils" / "proxy.py"
    assert helper.is_file(), (
        f"{module_path}: sys.path bootstrap uses parents[{indices[0]}] -> "
        f"{bootstrapped_root}, which does not contain the canonical helper "
        f"at {helper}."
    )


@pytest.mark.parametrize(
    "module_path",
    [
        "src/integration/youtube_api.py",
        "src/agents/process_video_with_mcp.py",
        "src/agents/interactive_metadata_extractor.py",
        "src/mcp/mcp_video_processor.py",
        "src/youtube_extension/backend/enhanced_video_processor.py",
        "src/youtube_extension/backend/services/youtube/adapters/robust.py",
        "src/youtube_extension/backend/services/youtube/adapters/official_api.py",
    ],
)
def test_module_resolves_proxy_config_from_the_canonical_helper(
    module_path: str,
) -> None:
    """Each transcript caller must source ``proxy_config`` from the helper.

    Guards against a module satisfying the keyword check with a hardcoded
    ``proxy_config=None``, which would pass the structural test while still
    bypassing the proxy.
    """
    path = PROJECT_ROOT / module_path
    assert path.is_file(), f"{module_path} does not exist — update this test"

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    calls = _client_constructions(tree)
    assert calls, f"{module_path} no longer constructs {CLIENT_NAME}"

    assert PROXY_HELPER in source, (
        f"{module_path} constructs {CLIENT_NAME} but never references "
        f"{PROXY_HELPER}; proxy_config is likely hardcoded."
    )

    # A mention is not enough: the call site alone satisfies the substring
    # check even when the import is broken or renamed. Require a real import
    # of the helper, bound under its canonical name.
    proxy_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == PROXY_MODULE
    ]
    assert proxy_imports, (
        f"{module_path} references {PROXY_HELPER} but never imports it from "
        f"{PROXY_MODULE}; the call site would raise NameError or silently "
        "resolve to something else."
    )

    # Every import path must bind the helper. The fallback bootstrap repeats
    # the import, so checking only that *some* statement binds it would let a
    # broken primary import through while the module still looks correct.
    for node in proxy_imports:
        binds_helper = any(
            alias.name == PROXY_HELPER and alias.asname in (None, PROXY_HELPER)
            for alias in node.names
        )
        assert binds_helper, (
            f"{module_path} line {node.lineno}: imports from {PROXY_MODULE} "
            f"without binding {PROXY_HELPER}. Every import path must provide "
            "the helper or the call site breaks."
        )

    for call in calls:
        literal_none = [
            kw
            for kw in call.keywords
            if kw.arg == REQUIRED_KEYWORD
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is None
        ]
        assert not literal_none, (
            f"{module_path}:{call.lineno} passes {REQUIRED_KEYWORD}=None "
            f"literally, which disables the proxy unconditionally. Use "
            f"{PROXY_HELPER}() instead."
        )


def test_proxy_helper_returns_none_without_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper must degrade to a direct connection, not raise.

    Every call site now invokes the helper unconditionally, so a raise here
    would break transcript fetching for every deployment that has no proxy.
    """
    from youtube_extension.utils.proxy import get_transcript_proxy_config

    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)
    assert get_transcript_proxy_config() is None


def test_proxy_helper_returns_config_carrying_the_url_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper must actually forward the configured URL.

    Composed with ``test_every_transcript_client_passes_proxy_config`` (every
    site passes ``proxy_config=<helper>()``) this closes the loop: the keyword
    is present *and* it carries a real proxy. Stubbed so the assertion holds
    without the optional ``youtube-transcript-api`` extra installed.
    """
    import importlib
    import types

    captured: dict[str, str] = {}

    class _StubProxyConfig:
        def __init__(self, http_url: str, https_url: str) -> None:
            captured["http"] = http_url
            captured["https"] = https_url

    stub = types.ModuleType("youtube_transcript_api.proxies")
    stub.GenericProxyConfig = _StubProxyConfig  # type: ignore[attr-defined]
    parent = types.ModuleType("youtube_transcript_api")
    parent.proxies = stub  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "youtube_transcript_api", parent)
    monkeypatch.setitem(sys.modules, "youtube_transcript_api.proxies", stub)

    proxy_module = importlib.reload(
        importlib.import_module("youtube_extension.utils.proxy")
    )
    try:
        url = "http://user:secret@proxy.example.com:8080"
        monkeypatch.setenv("WEBSHARE_PROXY_URL", url)

        config = proxy_module.get_transcript_proxy_config()

        assert config is not None, (
            "helper returned None despite WEBSHARE_PROXY_URL being set — every "
            "call site would silently egress directly"
        )
        assert isinstance(config, _StubProxyConfig)
        assert captured == {"http": url, "https": url}
    finally:
        # Restore the module against the real (or absent) dependency so later
        # tests in the session don't observe the stub.
        monkeypatch.undo()
        importlib.reload(importlib.import_module("youtube_extension.utils.proxy"))
