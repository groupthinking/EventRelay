from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_dockerfile_installs_apps_web_from_root_workspace_lockfile() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
    normalized = _normalized(dockerfile)
    lines = dockerfile.splitlines()

    assert any(
        all(token in line for token in ("COPY", "package.json", "package-lock.json", ".npmrc"))
        for line in lines
    )
    assert any(
        all(token in line for token in ("COPY", "apps/web/package.json", "./apps/web/package.json"))
        for line in lines
    )
    assert any(
        all(
            token in line
            for token in (
                "COPY",
                "apps/web/src/dataconnect-generated",
                "./apps/web/src/dataconnect-generated",
            )
        )
        for line in lines
    )
    assert "npm ci --workspace apps/web --omit=dev --ignore-scripts" in normalized
    assert "apps/web/package-lock.json" not in normalized


def test_dockerignore_reincludes_apps_web_for_workspace_install() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text()

    assert "apps/" in dockerignore
    assert "!apps/web/" in dockerignore
    assert "apps/web/node_modules/" in dockerignore
    assert "apps/web/.next/" in dockerignore
