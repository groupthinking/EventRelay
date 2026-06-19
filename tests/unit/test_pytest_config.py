from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


def test_pytest_default_addopts_do_not_enforce_coverage() -> None:
    parser = ConfigParser()
    parser.read(Path(__file__).resolve().parents[2] / "pytest.ini")

    addopts = parser["pytest"]["addopts"]

    assert "--cov=" not in addopts
    assert "--cov-fail-under" not in addopts
