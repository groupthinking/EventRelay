#!/usr/bin/env python3
"""
Command Line Interface for UVAI YouTube Extension
Provides CLI commands for development, testing, and deployment
"""

import typer
from pathlib import Path
import subprocess
import sys
import os
from typing import Optional

app = typer.Typer(
    name="youtube-extension",
    help="UVAI YouTube Extension CLI",
    add_completion=False,
)

@app.callback()
def callback():
    """UVAI YouTube Extension - AI-Powered Video Learning Platform"""
    pass

@app.command()
def main():
    """Main CLI entry point"""
    typer.echo("🎯 UVAI YouTube Extension CLI")
    typer.echo("Run 'youtube-extension --help' for available commands")

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
):
    """Start the FastAPI development server"""
    typer.echo(f"🚀 Starting server on {host}:{port}")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "youtube_extension.main:app",
        "--host", host,
        "--port", str(port),
    ]

    if reload:
        cmd.append("--reload")

    try:
        subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    except KeyboardInterrupt:
        typer.echo("\n👋 Server stopped")
    except Exception as e:
        typer.echo(f"❌ Error starting server: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def test(
    verbose: bool = typer.Option(False, "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, help="Run with coverage"),
):
    """Run test suite"""
    typer.echo("🧪 Running tests...")

    cmd = [sys.executable, "-m", "pytest", "tests/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=youtube_extension", "--cov-report=html"])

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)

@app.command()
def migrate():
    """Run database migrations"""
    typer.echo("🗄️ Running database migrations...")

    # Import here to avoid circular imports
    try:
        from youtube_extension.backend.config.database import run_migrations
        run_migrations()
        typer.echo("✅ Migrations completed successfully")
    except ImportError as e:
        typer.echo(f"❌ Migration module not found: {e}", err=True)
        typer.echo("💡 Make sure you're in the correct directory and dependencies are installed")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Migration failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def lint():
    """Run code quality checks"""
    typer.echo("🔍 Running code quality checks...")

    project_root = Path(__file__).parent.parent.parent

    # Run ruff
    typer.echo("Running ruff...")
    result = subprocess.run([
        sys.executable, "-m", "ruff", "check", "src/youtube_extension/"
    ], cwd=project_root)

    if result.returncode != 0:
        typer.echo("❌ Ruff checks failed", err=True)
        raise typer.Exit(1)

    # Run mypy
    typer.echo("Running mypy...")
    result = subprocess.run([
        sys.executable, "-m", "mypy", "src/youtube_extension/"
    ], cwd=project_root)

    if result.returncode != 0:
        typer.echo("❌ MyPy checks failed", err=True)
        raise typer.Exit(1)

    typer.echo("✅ All code quality checks passed")

@app.command()
def format():
    """Format code with black and isort"""
    typer.echo("🎨 Formatting code...")

    project_root = Path(__file__).parent.parent.parent

    # Run black
    typer.echo("Running black...")
    subprocess.run([
        sys.executable, "-m", "black", "src/youtube_extension/"
    ], cwd=project_root)

    # Run isort
    typer.echo("Running isort...")
    subprocess.run([
        sys.executable, "-m", "isort", "src/youtube_extension/"
    ], cwd=project_root)

    typer.echo("✅ Code formatting completed")

@app.command()
def install():
    """Install the package in development mode"""
    typer.echo("📦 Installing package in development mode...")

    project_root = Path(__file__).parent.parent.parent
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "-e", "."
    ], cwd=project_root)

    if result.returncode != 0:
        typer.echo("❌ Installation failed", err=True)
        raise typer.Exit(1)

    typer.echo("✅ Package installed successfully")

@app.command()
def health():
    """Check system health"""
    typer.echo("🏥 Checking system health...")

    checks = []

    # Check if virtual environment is active
    venv_active = "VIRTUAL_ENV" in os.environ
    checks.append(("Virtual Environment", "✅ Active" if venv_active else "❌ Not active"))

    # Check package import
    try:
        import youtube_extension
        checks.append(("Package Import", "✅ Working"))
    except ImportError:
        checks.append(("Package Import", "❌ Failed"))

    # Check FastAPI app
    try:
        from youtube_extension.main import app
        checks.append(("FastAPI App", "✅ Loaded"))
    except ImportError:
        checks.append(("FastAPI App", "❌ Failed"))

    # Print results
    for check, status in checks:
        typer.echo(f"  {check}: {status}")

    # Overall status
    all_passed = all("✅" in status for _, status in checks)
    if all_passed:
        typer.echo("\n🎉 All health checks passed!")
    else:
        typer.echo("\n⚠️ Some health checks failed")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
