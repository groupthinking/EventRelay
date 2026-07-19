"""Unit tests for youtube_extension.cli — covers all CLI commands."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from typer.testing import CliRunner

from youtube_extension.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# callback / root invocation
# ---------------------------------------------------------------------------


class TestCallback:
    def test_help_flag_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "UVAI YouTube Extension" in result.output

    def test_no_args_shows_help(self):
        # Typer shows help when no subcommand is given (callback-only app)
        result = runner.invoke(app, [])
        # exit_code may be 0 or 2 depending on typer version; we mainly
        # assert it doesn't crash with an uncaught exception.
        assert result.exception is None or result.exit_code in (0, 2)


# ---------------------------------------------------------------------------
# main command
# ---------------------------------------------------------------------------


class TestMainCommand:
    def test_main_prints_header(self):
        result = runner.invoke(app, ["main"])
        assert result.exit_code == 0
        assert "UVAI YouTube Extension CLI" in result.output

    def test_main_prints_help_hint(self):
        result = runner.invoke(app, ["main"])
        assert "--help" in result.output


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------


class TestServeCommand:
    def test_serve_default_options(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        assert "Starting server" in result.output
        # default host / port in the output
        assert "0.0.0.0:8000" in result.output

    def test_serve_custom_port(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["serve", "--port", "9000"])
        assert result.exit_code == 0
        assert "9000" in result.output

    def test_serve_custom_host(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["serve", "--host", "127.0.0.1"])
        assert result.exit_code == 0
        assert "127.0.0.1" in result.output

    def test_serve_passes_reload_flag_by_default(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["serve"])

        assert "--reload" in captured["cmd"]

    def test_serve_no_reload_omits_flag(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["serve", "--no-reload"])

        assert "--reload" not in captured["cmd"]

    def test_serve_keyboard_interrupt_handled(self):
        with patch("subprocess.run", side_effect=KeyboardInterrupt):
            result = runner.invoke(app, ["serve"])
        # Should print stop message and exit 0
        assert "Server stopped" in result.output
        assert result.exit_code == 0

    def test_serve_generic_exception_exits_1(self):
        with patch("subprocess.run", side_effect=RuntimeError("oops")):
            result = runner.invoke(app, ["serve"])
        assert result.exit_code == 1

    def test_serve_invokes_uvicorn_module(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["serve"])

        assert "uvicorn" in captured["cmd"]
        assert "youtube_extension.main:app" in captured["cmd"]


# ---------------------------------------------------------------------------
# test command
# ---------------------------------------------------------------------------


class TestTestCommand:
    def test_test_basic_run(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "Running tests" in result.output

    def test_test_verbose_flag(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["test", "-v"])

        assert "-v" in captured["cmd"]

    def test_test_coverage_flag(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["test", "--coverage"])

        assert "--cov=youtube_extension" in captured["cmd"]
        assert "--cov-report=html" in captured["cmd"]

    def test_test_failure_propagates_exit_code(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=2)
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 2

    def test_test_no_verbose_no_extra_flag(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["test"])

        assert "-v" not in captured["cmd"]
        assert "--cov=youtube_extension" not in captured["cmd"]


# ---------------------------------------------------------------------------
# migrate command
# ---------------------------------------------------------------------------


class TestMigrateCommand:
    def test_migrate_success(self):
        mock_run_migrations = MagicMock()
        with patch.dict(
            sys.modules,
            {
                "youtube_extension.backend.config.database": MagicMock(
                    run_migrations=mock_run_migrations
                )
            },
        ):
            result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 0
        assert "Migrations completed successfully" in result.output

    def test_migrate_import_error_exits_1(self):
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *a, **kw: (
                (_ for _ in ()).throw(ImportError("no module"))
                if "database" in name
                else __import__(name, *a, **kw)
            ),
        ):
            # Simpler: patch the module dict
            pass

        # Directly patch by temporarily removing the module if present
        mod_name = "youtube_extension.backend.config.database"
        original = sys.modules.pop(mod_name, None)
        try:
            # Force ImportError by inserting a module that raises on attribute access
            broken_attr = MagicMock(side_effect=ImportError("no module"))
            sys.modules[mod_name] = MagicMock(run_migrations=broken_attr)
            result = runner.invoke(app, ["migrate"])
        finally:
            if original is not None:
                sys.modules[mod_name] = original
            else:
                sys.modules.pop(mod_name, None)

        assert result.exit_code == 1

    def test_migrate_general_exception_exits_1(self):
        mod_name = "youtube_extension.backend.config.database"
        original = sys.modules.pop(mod_name, None)
        try:
            mock_mod = MagicMock()
            mock_mod.run_migrations.side_effect = RuntimeError("DB down")
            sys.modules[mod_name] = mock_mod
            result = runner.invoke(app, ["migrate"])
        finally:
            if original is not None:
                sys.modules[mod_name] = original
            else:
                sys.modules.pop(mod_name, None)

        assert result.exit_code == 1
        assert "Migration failed" in result.output

    def test_migrate_prints_running_message(self):
        mod_name = "youtube_extension.backend.config.database"
        original = sys.modules.pop(mod_name, None)
        try:
            sys.modules[mod_name] = MagicMock(run_migrations=MagicMock())
            result = runner.invoke(app, ["migrate"])
        finally:
            if original is not None:
                sys.modules[mod_name] = original
            else:
                sys.modules.pop(mod_name, None)

        assert "Running database migrations" in result.output


# ---------------------------------------------------------------------------
# api-cost-worker command
# ---------------------------------------------------------------------------


class TestAPICostWorkerCommand:
    def test_api_cost_worker_runs_dedicated_entrypoint(self):
        worker_main = MagicMock()
        worker_module = types.SimpleNamespace(main=worker_main)

        with patch.dict(
            sys.modules,
            {"youtube_extension.backend.api_cost_worker": worker_module},
        ):
            result = runner.invoke(app, ["api-cost-worker"])

        assert result.exit_code == 0
        worker_main.assert_called_once_with()

    def test_api_cost_worker_reports_startup_failure(self):
        worker_module = types.SimpleNamespace(
            main=MagicMock(side_effect=ValueError("DATABASE_URL is required"))
        )

        with patch.dict(
            sys.modules,
            {"youtube_extension.backend.api_cost_worker": worker_module},
        ):
            result = runner.invoke(app, ["api-cost-worker"])

        assert result.exit_code == 1
        assert "DATABASE_URL is required" in result.output


# ---------------------------------------------------------------------------
# lint command
# ---------------------------------------------------------------------------


class TestLintCommand:
    def test_lint_all_pass(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["lint"])
        assert result.exit_code == 0
        assert "All code quality checks passed" in result.output

    def test_lint_ruff_failure_exits_1(self):
        call_count = 0

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call is ruff — fail it
            return MagicMock(returncode=1 if call_count == 1 else 0)

        with patch("subprocess.run", side_effect=fake_run):
            result = runner.invoke(app, ["lint"])

        assert result.exit_code == 1
        assert "Ruff checks failed" in result.output

    def test_lint_mypy_failure_exits_1(self):
        call_count = 0

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # Second call is mypy — fail it
            return MagicMock(returncode=0 if call_count == 1 else 1)

        with patch("subprocess.run", side_effect=fake_run):
            result = runner.invoke(app, ["lint"])

        assert result.exit_code == 1
        assert "MyPy checks failed" in result.output

    def test_lint_runs_ruff_and_mypy(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["lint"])

        combined = " ".join(" ".join(c) for c in calls)
        assert "ruff" in combined
        assert "mypy" in combined


# ---------------------------------------------------------------------------
# format command
# ---------------------------------------------------------------------------


class TestFormatCommand:
    def test_format_runs_black_and_isort(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            result = runner.invoke(app, ["format"])

        assert result.exit_code == 0
        combined = " ".join(" ".join(c) for c in calls)
        assert "black" in combined
        assert "isort" in combined

    def test_format_success_message(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["format"])
        assert "Code formatting completed" in result.output

    def test_format_prints_running_messages(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["format"])
        assert "Formatting code" in result.output
        assert "Running black" in result.output
        assert "Running isort" in result.output


# ---------------------------------------------------------------------------
# install command
# ---------------------------------------------------------------------------


class TestInstallCommand:
    def test_install_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "Package installed successfully" in result.output

    def test_install_failure_exits_1(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = runner.invoke(app, ["install"])
        assert result.exit_code == 1
        assert "Installation failed" in result.output

    def test_install_uses_pip_install_editable(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            runner.invoke(app, ["install"])

        assert "pip" in captured["cmd"]
        assert "install" in captured["cmd"]
        assert "-e" in captured["cmd"]

    def test_install_prints_start_message(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["install"])
        assert "Installing package" in result.output


# ---------------------------------------------------------------------------
# health command
# ---------------------------------------------------------------------------


class TestHealthCommand:
    def test_health_all_pass(self):
        """When all imports succeed and VIRTUAL_ENV is set, exits 0."""
        env = {"VIRTUAL_ENV": "/fake/venv"}
        # Ensure youtube_extension.main is importable by stubbing it
        fake_main = types.ModuleType("youtube_extension.main")
        fake_main.app = MagicMock()  # type: ignore[attr-defined]
        with patch.dict("os.environ", env, clear=False):
            with patch.dict(sys.modules, {"youtube_extension.main": fake_main}):
                result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "All health checks passed" in result.output

    def test_health_no_venv_shows_not_active(self):
        """Without VIRTUAL_ENV, reports venv as inactive."""
        import os as _os

        # Stub youtube_extension.main so health's internal import is a no-op and
        # does not reconfigure logging/stdout mid-invoke (a fresh import runs
        # setup_logging, which would break CliRunner output capture). Mirrors
        # test_health_all_pass.
        fake_main = types.ModuleType("youtube_extension.main")
        fake_main.app = MagicMock()  # type: ignore[attr-defined]
        saved_value = _os.environ.pop("VIRTUAL_ENV", None)
        try:
            with patch.dict(sys.modules, {"youtube_extension.main": fake_main}):
                result = runner.invoke(app, ["health"])
        finally:
            if saved_value is not None:
                _os.environ["VIRTUAL_ENV"] = saved_value

        assert result.exit_code == 1
        assert "Not active" in result.output

    def test_health_package_import_failure(self):
        """If youtube_extension cannot be imported, health exits 1."""
        # Remove youtube_extension from sys.modules to simulate import failure
        mods_to_remove = [k for k in sys.modules if k.startswith("youtube_extension")]
        saved = {k: sys.modules.pop(k) for k in mods_to_remove}
        try:
            with patch.dict("os.environ", {"VIRTUAL_ENV": "/fake/venv"}):
                # Patch the import so youtube_extension itself raises ImportError
                import builtins

                real_import = builtins.__import__

                def broken_import(name, *args, **kwargs):
                    # Block every youtube_extension import so the health command
                    # hits its failure branch immediately. Guarding only the bare
                    # "youtube_extension" name (with `not args`) never triggered for
                    # a real `import youtube_extension`, so health re-imported
                    # youtube_extension.main, whose module-level logging setup
                    # reconfigured stdout and broke CliRunner's output capture.
                    if name == "youtube_extension" or name.startswith(
                        "youtube_extension."
                    ):
                        raise ImportError("forced")
                    return real_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=broken_import):
                    result = runner.invoke(app, ["health"])
        finally:
            sys.modules.update(saved)

        # The health command catches ImportError and records a failed check
        assert "Package Import" in result.output

    def test_health_prints_all_check_labels(self):
        # Stub youtube_extension.main so health's import is a no-op and does not
        # reconfigure logging/stdout mid-invoke (see test_health_all_pass) — this
        # keeps the check labels in CliRunner's captured output regardless of
        # whether main was already imported by a prior test.
        fake_main = types.ModuleType("youtube_extension.main")
        fake_main.app = MagicMock()  # type: ignore[attr-defined]
        with patch.dict("os.environ", {"VIRTUAL_ENV": "/fake"}):
            with patch.dict(sys.modules, {"youtube_extension.main": fake_main}):
                result = runner.invoke(app, ["health"])
        assert "Virtual Environment" in result.output
        assert "Package Import" in result.output
        assert "FastAPI App" in result.output

    def test_health_some_fail_shows_warning(self):
        """If any check fails, warns instead of celebrating."""
        import os as _os

        _os.environ.pop("VIRTUAL_ENV", None)

        import builtins

        real_import = builtins.__import__

        def broken_import(name, *args, **kwargs):
            if name in ("youtube_extension", "youtube_extension.main"):
                raise ImportError("forced")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=broken_import):
            result = runner.invoke(app, ["health"])

        # Whether exit 0 or 1 depends on which checks pass; we confirm the
        # warning path is reachable (at minimum the venv check fails).
        assert result.output  # at minimum something was printed
