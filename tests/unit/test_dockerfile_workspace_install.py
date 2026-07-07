from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_dockerfile_installs_apps_web_from_root_workspace_lockfile() -> None:
    dockerfile = _normalized((PROJECT_ROOT / "Dockerfile").read_text())

    assert "COPY package.json package-lock.json .npmrc ./" in dockerfile
    assert "COPY apps/web/package.json ./apps/web/package.json" in dockerfile
    assert (
        "COPY apps/web/src/dataconnect-generated "
        "./apps/web/src/dataconnect-generated" in dockerfile
    )
    assert "npm ci --workspace apps/web --omit=dev --ignore-scripts" in dockerfile
    assert "apps/web/package-lock.json" not in dockerfile


def test_dockerignore_reincludes_apps_web_for_workspace_install() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text()

    assert "apps/" in dockerignore
    assert "!apps/web/" in dockerignore
    assert "apps/web/node_modules/" in dockerignore
    assert "apps/web/.next/" in dockerignore
