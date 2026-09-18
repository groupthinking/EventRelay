from __future__ import annotations

from pathlib import Path
import tomllib


CONFIG_PATH = Path(__file__).resolve().parents[2] / ".gitleaks.toml"


def _load_config() -> dict:
    assert CONFIG_PATH.exists(), ".gitleaks.toml should exist"
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def test_gitleaks_allowlists_web_api_route_tests_with_dummy_provider_tokens() -> None:
    config = _load_config()
    paths = config["allowlist"]["paths"]

    assert "tests/.*" in paths
    assert "apps/web/src/app/api/__tests__/.*" in paths, (
        "secret scanning must allowlist the web API route tests that pin "
        "sanitized OpenAI/Stripe token-shaped fixtures"
    )
