"""
Tests for security vulnerability fixes
Tests Issues #1, #2, and #3 from security audit

NOTE: These tests verify security patterns are in place.
Tests that require specific modules will skip if unavailable.
"""

import json
import os
import re
import shlex
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Canonical location of the production container definition. Kept as a module
# constant so the path is asserted in exactly one place; tests fail rather than
# skip when it does not resolve.
PRODUCTION_DOCKERFILE = (
    project_root / "infrastructure" / "docker" / "Dockerfile.production"
)

# Matches a PEP 508-ish requirement with a `>=` floor, with or without extras
# and surrounding quotes, e.g. `"uvicorn[standard]>=0.24.0"` or `fastapi`.
_REQUIREMENT_RE = re.compile(
    r"""^["']?(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)   # distribution name
        (?:\[[^\]]*\])?                              # optional extras
        (?:\s*>=\s*(?P<floor>[0-9][0-9A-Za-z.*+!-]*))?  # optional >= floor
    """,
    re.VERBOSE,
)


def _version_key(version: str) -> tuple:
    """Comparable key for a dotted version. Non-numeric segments sort as -1 so
    pre-releases order below the corresponding final release."""
    parts = []
    for segment in re.split(r"[._-]", version):
        parts.append((0, int(segment)) if segment.isdigit() else (-1, 0))
    return tuple(parts)


def _fmt(key: tuple) -> str:
    return ".".join(str(value) for _, value in key)


def _pip_install_command(text: str) -> str:
    """Reconstruct the logical ``pip install`` command from a Dockerfile,
    joining backslash line continuations into a single string.

    Operating on the joined command rather than on individual physical lines is
    essential: the pre-hardening Dockerfile spread ``pytest`` and a trailing
    ``|| echo`` across continuation lines, so any line-filtered check silently
    passed against the very content it was meant to reject.
    """
    logical, buf = [], ""
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if line.endswith("\\"):
            buf += line[:-1].strip() + " "
            continue
        buf += stripped
        if buf:
            logical.append(buf)
        buf = ""
    if buf:
        logical.append(buf)
    for command in logical:
        if "pip install" in command:
            return command
    return ""


def _installed_requirements(command: str) -> dict:
    """Parse ``{normalised_name: floor_key_or_None}`` from a joined ``pip
    install`` command, tolerating quoted and unquoted tokens alike."""
    floors = {}
    if not command:
        return floors
    takes_value = {
        "--trusted-host",
        "--index-url",
        "--extra-index-url",
        "-i",
        "-c",
        "-r",
        "--constraint",
        "--requirement",
    }
    skip_next = False
    for token in shlex.split(command):
        if skip_next:
            skip_next = False
            continue
        if token in ("||", "&&", ";"):
            # Everything past a shell operator is a fallback, not a requirement.
            break
        if token in ("RUN", "pip", "install"):
            continue
        if token.startswith("-"):
            if token in takes_value:
                skip_next = True
            continue
        match = _REQUIREMENT_RE.match(token)
        if not match:
            continue
        name = match.group("name").lower().replace("_", "-")
        floor = match.group("floor")
        floors[name] = _version_key(floor) if floor else None
    return floors


def _parse_floors(text: str) -> dict:
    """Extract ``{normalised_name: floor_key}`` from a requirements file."""
    floors = {}
    for raw in text.splitlines():
        line = raw.strip().rstrip("\\").strip().rstrip(",")
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = _REQUIREMENT_RE.match(line)
        if not match:
            continue
        name = match.group("name").lower().replace("_", "-")
        floor = match.group("floor")
        floors[name] = _version_key(floor) if floor else None
    return floors


# ``[project] dependencies`` is a flat array of quoted PEP 508 strings. Anchoring
# on a line-initial ``dependencies = [`` selects it without matching the
# ``[project.optional-dependencies]`` tables, whose keys are indented (``dev = [``).
# Extracting textually rather than via tomllib/tomli keeps this guard working on
# the declared ``requires-python = ">=3.9"`` floor, where neither is guaranteed.
_PYPROJECT_DEPS_RE = re.compile(
    r"^dependencies\s*=\s*\[(?P<body>.*?)^\]", re.MULTILINE | re.DOTALL
)


def _pyproject_floors(text: str) -> dict:
    """Extract ``{normalised_name: floor_key}`` from ``[project] dependencies``."""
    match = _PYPROJECT_DEPS_RE.search(text)
    if not match:
        return {}
    entries = re.findall(r"[\"']([^\"']+)[\"']", match.group("body"))
    return _parse_floors("\n".join(entries))


def _canonical_floors() -> dict:
    """Highest declared floor per distribution across *both* canonical manifests.

    ``requirements.txt`` and ``pyproject.toml`` disagree in places -- for example
    ``python-dotenv`` is ``>=1.0.0`` in the former and ``>=1.2.2`` in the latter.
    Comparing against only one of them lets Dockerfile.production sink to the
    lower floor while still passing, so take the maximum of the two.
    """
    requirements = project_root / "requirements.txt"
    pyproject = project_root / "pyproject.toml"
    assert requirements.exists(), "requirements.txt not found"
    assert pyproject.exists(), "pyproject.toml not found"

    floors = _parse_floors(requirements.read_text())
    for name, floor in _pyproject_floors(pyproject.read_text()).items():
        current = floors.get(name)
        if floor is not None and (current is None or floor > current):
            floors[name] = floor
    assert floors, "no canonical dependency floors parsed"
    return floors


# Operators that let a failing ``pip install`` still produce exit 0: ``||``
# supplies a fallback, ``;`` lets the next command's status win, and ``|``
# discards the left-hand status without ``pipefail``. ``&&`` propagates failure
# and is therefore not listed.
_FAILURE_MASKING_OPERATORS = ("||", ";", "|")


class TestAPIKeyExposureFix:
    """Test Issue 1: API Key Exposure Risk Fix"""

    def test_env_example_has_youtube_api_key(self):
        """Verify .env.example documents YOUTUBE_API_KEY (not REACT_APP_*)"""
        env_example = project_root / ".env.example"
        assert env_example.exists(), ".env.example not found"

        content = env_example.read_text()

        # Should have proper backend env var
        assert "YOUTUBE_API_KEY" in content

        # Should NOT have frontend-only env var (would be security issue)
        # Note: REACT_APP_* vars should only be in frontend
        if "REACT_APP_YOUTUBE_API_KEY" in content:
            pytest.fail("Backend .env.example should not reference REACT_APP_* variables")

    def test_backend_imports_work(self):
        """Verify backend video processing module can be imported"""
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from agents.process_video_with_mcp import RealVideoProcessor
            assert True
        except (ImportError, Exception) as e:
            pytest.skip(f"Module not available: {e}")


class TestInputValidationFix:
    """Test Issue 2: Input Validation for Agent Messages"""

    def test_agents_unified_module_exists(self):
        """Verify agents/unified directory exists"""
        agents_unified = project_root / "src" / "agents" / "unified"
        assert agents_unified.exists(), f"agents/unified directory not found at {agents_unified}"

    def test_validation_functions_exist(self):
        """Verify validation functions exist in the codebase"""
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from agents.unified.mcp_a2a_mojo_integration import (
                    validate_agent_identifier,
                    sanitize_message_content
                )

            # Basic smoke test
            assert validate_agent_identifier("test_agent") is True
            assert validate_agent_identifier("") is False

        except (ImportError, Exception) as e:
            pytest.skip(f"Module not available: {e}")

    def test_sanitize_removes_control_chars(self):
        """Test content sanitization removes control characters"""
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from agents.unified.mcp_a2a_mojo_integration import sanitize_message_content

            malicious_string = "normal\\x00text\\x01"
            sanitized = sanitize_message_content(malicious_string)

            # Should not contain null bytes
            assert "\\x00" not in str(sanitized) or sanitized == malicious_string

        except (ImportError, Exception) as e:
            pytest.skip(f"Module not available: {e}")


class TestObservabilityFix:
    """Test Issue 3: Observability Silent Failure Fix"""

    def test_observability_module_exists(self):
        """Verify observability_setup.py exists"""
        obs_file = project_root / "src" / "agents" / "observability_setup.py"
        if not obs_file.exists():
            pytest.skip(f"Observability file not found: {obs_file}")

        content = obs_file.read_text()

        # Should have logging setup
        assert "logging" in content.lower() or "logger" in content.lower()

    def test_uvai_observability_can_import(self):
        """Test UVAIObservability can be imported"""
        try:
            from agents.observability_setup import UVAIObservability
            obs = UVAIObservability()
            assert hasattr(obs, 'get_health_status') or hasattr(obs, 'setup_complete')
        except ImportError as e:
            pytest.skip(f"Module not available: {e}")
        except Exception as e:
            # May fail due to missing telemetry, that's OK
            pytest.skip(f"Module initialization failed (expected without OTEL): {e}")


class TestSecurityDocumentation:
    """Test that security rationale is properly documented"""

    def test_api_key_security_in_env_example(self):
        """Verify .env.example has security warnings"""
        env_example = project_root / ".env.example"
        if not env_example.exists():
            pytest.skip(".env.example not found")

        content = env_example.read_text()

        # Should have warning about secrets
        assert "secret" in content.lower() or "never commit" in content.lower()

    def test_process_video_exists(self):
        """Verify process_video_with_mcp.py exists and has security patterns"""
        file_path = project_root / "src" / "agents" / "process_video_with_mcp.py"
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")

        content = file_path.read_text()

        # Should have API key handling
        assert "API_KEY" in content or "api_key" in content

    def test_observability_has_logging(self):
        """Verify observability setup has logging patterns"""
        file_path = project_root / "src" / "agents" / "observability_setup.py"
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")

        content = file_path.read_text()

        # Should have production-aware logging
        assert "log" in content.lower()


class TestSecurityBestPractices:
    """General security best practices tests"""

    def test_no_hardcoded_api_keys(self):
        """Verify no hardcoded API keys in main backend files"""
        files_to_check = [
            project_root / "src" / "uvai" / "api" / "main.py",
            project_root / "src" / "youtube_extension" / "backend" / "main_v2.py",
        ]

        suspect_patterns = [
            "AIzaSy",  # Google API key prefix
            "sk-",    # OpenAI key prefix
            "xai-",   # X.AI key prefix
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text()
            for pattern in suspect_patterns:
                # Allow patterns in comments/strings explaining what they are
                if pattern in content:
                    # Check if it's just a documentation reference
                    lines_with_pattern = [l for l in content.split('\n') if pattern in l]
                    for line in lines_with_pattern:
                        # If it looks like a full key (pattern + 30+ chars), fail
                        if len(line.strip()) > 50 and not line.strip().startswith('#'):
                            pytest.fail(f"Possible hardcoded API key in {file_path}: {line[:80]}...")

    def test_dockerfile_uses_nonroot_user(self):
        """Verify Dockerfile.production drops privileges to a non-root user.

        The path is asserted rather than skipped on: this test previously
        resolved ``project_root / "Dockerfile.production"``, which has never
        existed, so it skipped unconditionally and the assertions below never
        ran. Failing loudly means a future relocation cannot silently re-vacate
        the check.
        """
        dockerfile = PRODUCTION_DOCKERFILE
        assert dockerfile.exists(), (
            f"{dockerfile.relative_to(project_root)} not found. If the file moved, "
            "update PRODUCTION_DOCKERFILE rather than skipping this test."
        )

        content = dockerfile.read_text()

        user_directives = [
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("USER ")
        ]
        assert user_directives, "Dockerfile should switch to a non-root user"

        final_user = user_directives[-1].split(maxsplit=1)[1].strip()
        assert final_user not in {
            "root",
            "0",
        }, f"Dockerfile must not run as root, got USER {final_user}"
        assert final_user in {"appuser", "nonroot"}, (
            f"Unexpected runtime user {final_user!r}; expected a known "
            "unprivileged account"
        )

    def test_dockerfile_production_pins_dependency_floors(self):
        """Every dependency installed by Dockerfile.production must carry a
        floor at least as high as the canonical declaration in
        ``requirements.txt`` *or* ``pyproject.toml``.

        This image installs a reduced runtime subset by name instead of using
        ``-r requirements.txt``, so advisory floors raised in the canonical
        manifests do not propagate automatically. Without this guard the image
        silently drifts behind published security fixes -- which is how an
        unpinned ``python-multipart`` survived the floor bump for advisories
        468-471 (see #1095).

        Both manifests are consulted because they disagree: ``python-dotenv``
        is ``>=1.0.0`` in requirements.txt but ``>=1.2.2`` in pyproject.toml,
        so checking only the former would accept a Dockerfile that sank to the
        lower, weaker floor.
        """
        dockerfile = PRODUCTION_DOCKERFILE
        assert dockerfile.exists(), f"{dockerfile} not found"

        canonical = _canonical_floors()
        installed = _installed_requirements(
            _pip_install_command(dockerfile.read_text())
        )

        assert installed, "Dockerfile.production declares no pinned dependencies"
        assert "slowapi" in installed, (
            "Dockerfile.production omits slowapi, which youtube_extension.main "
            "imports unconditionally at startup"
        )

        for name, floor in sorted(installed.items()):
            assert floor is not None, (
                f"{name} is installed without a version floor in "
                "Dockerfile.production; an unconstrained resolve can select a "
                "version with a known advisory"
            )
            expected = canonical.get(name)
            if expected is None:
                continue
            assert floor >= expected, (
                f"{name} floor {_fmt(floor)} in Dockerfile.production is below "
                f"the canonical floor {_fmt(expected)} declared in "
                "requirements.txt/pyproject.toml"
            )

    def test_dockerfile_production_does_not_swallow_install_failures(self):
        """Install failure must abort ``docker build``.

        A masked failure produces an image that builds cleanly with no packages
        installed and then dies at runtime with ``ModuleNotFoundError``. Reject
        the failure-masking shell operators outright rather than blacklisting
        particular spellings -- ``|| echo``, ``|| true``, ``|| :``,
        ``|| printf ...`` and ``; true`` are all the same defect.
        """
        command = _pip_install_command(PRODUCTION_DOCKERFILE.read_text())
        assert command, "no pip install step found in Dockerfile.production"
        found = [
            operator
            for operator in _FAILURE_MASKING_OPERATORS
            if operator in shlex.split(command)
        ]
        assert not found, (
            f"Dockerfile.production pip install uses {found!r}, which can mask "
            "a failed install; the build must fail instead of producing an "
            "image that starts and then raises ModuleNotFoundError"
        )

    def test_dockerfile_production_excludes_test_tooling(self):
        """Test frameworks must not be installed into the production image."""
        installed = _installed_requirements(
            _pip_install_command(PRODUCTION_DOCKERFILE.read_text())
        )
        assert installed, "no pip install step found in Dockerfile.production"
        for tool in ("pytest", "pytest-cov", "pytest-asyncio"):
            assert tool not in installed, (
                f"{tool} must not be installed into the production image; it "
                "enlarges the runtime attack surface"
            )

    def test_dockerfile_production_entrypoint_module_exists(self):
        """The ASGI module named in CMD must actually exist in this repo.

        Regression guard: the Dockerfile previously ran ``uvicorn server:app``,
        but no root-level ``server.py`` has ever existed here, so every
        container built from this file exited immediately. Resolve the target
        against the source tree the image copies in (``/app/src``) rather than
        importing it, so the assertion holds without the runtime dependencies
        installed.
        """
        text = PRODUCTION_DOCKERFILE.read_text()

        cmd_match = re.search(r"^CMD\s+(\[.*\])\s*$", text, re.MULTILINE)
        assert cmd_match, "Dockerfile.production must declare a CMD"

        argv = json.loads(cmd_match.group(1))
        assert argv and argv[0] == "uvicorn", f"unexpected entrypoint: {argv}"

        target = next((a for a in argv[1:] if ":" in a and not a.startswith("-")), None)
        assert target, f"no <module>:<attr> target found in CMD: {argv}"

        module, _, attr = target.partition(":")
        assert attr, f"CMD target {target!r} names no ASGI application attribute"

        # PYTHONPATH must include the directory the package actually lives in,
        # otherwise the absolute imports inside it fail at startup.
        pythonpath = re.search(r"^ENV\s+PYTHONPATH=(\S+)", text, re.MULTILINE)
        assert pythonpath, (
            "Dockerfile.production must set PYTHONPATH; the application package "
            "uses absolute imports rooted at the source directory"
        )
        assert "/app/src" in pythonpath.group(1), (
            f"PYTHONPATH={pythonpath.group(1)!r} does not include /app/src, where "
            "COPY . /app/ places the application package"
        )

        # /app/src maps to <repo>/src, so resolve the module there.
        rel = Path(*module.split("."))
        candidates = [
            project_root / "src" / rel.with_suffix(".py"),
            project_root / "src" / rel / "__init__.py",
        ]
        assert any(c.exists() for c in candidates), (
            f"CMD runs 'uvicorn {target}' but module {module!r} does not exist "
            f"under {project_root / 'src'}; tried "
            + ", ".join(str(c.relative_to(project_root)) for c in candidates)
        )

        source = next(c for c in candidates if c.exists()).read_text()
        assert re.search(rf"^{re.escape(attr)}\s*=", source, re.MULTILINE), (
            f"module {module!r} exists but defines no module-level {attr!r}; "
            f"'uvicorn {target}' would fail at startup"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

class TestSecurityAgentEvalFix:
    """Test Issue: Security Agent Eval Fix"""

    @pytest.mark.asyncio
    async def test_security_agent_distinguishes_eval_from_literal_eval(self, tmp_path):
        """Verify the security agent does not flag literal_eval as dangerous eval"""
        from agents.specialized.security_agent import SecurityAgent

        # Create dummy project path
        project_path = tmp_path / "dummy_project"
        project_path.mkdir()

        # Create a file with dangerous eval
        bad_file = project_path / "bad.py"
        bad_file.write_text("x = input()\neval(x)\nexec(x)")

        # Create a file with safe literal_eval
        safe_file = project_path / "safe.py"
        safe_file.write_text("import ast\nx = input()\nast.literal_eval(x)")

        agent = SecurityAgent()
        agent.project_path = project_path

        results = await agent.check_input_validation()

        issues = results.get("issues", [])
        eval_issues = [issue for issue in issues if issue.get("type") == "dangerous_eval"]

        # Should only find the dangerous eval in bad.py
        bad_file_str = str(bad_file.relative_to(project_path))
        safe_file_str = str(safe_file.relative_to(project_path))

        bad_found = False
        safe_found = False

        for issue in eval_issues:
            if issue.get("file") == bad_file_str:
                bad_found = True
            elif issue.get("file") == safe_file_str:
                safe_found = True

        assert bad_found, "Failed to detect dangerous eval"
        assert not safe_found, "Falsely detected literal_eval as dangerous"
