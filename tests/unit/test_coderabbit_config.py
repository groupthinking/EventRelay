"""Tests for .coderabbit.yaml configuration.

Validates the fields added or changed in the PR that version-controlled
CodeRabbit settings from the dashboard into the repository:
  - inheritance
  - auto_assign_reviewers
  - auto_review.drafts (true) and ignore_title_keywords
  - finishing_touches
  - path_filters
  - new path_instructions entry for sdk/python/eventrelay_sdk/**
  - tools.presidio
  - knowledge_base.linear and knowledge_base.mcp
  - issue_enrichment
"""

from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

def _find_repo_root(start: Path) -> Path:
    """Walk up from *start* until a directory containing ``.git`` is found.

    This is more robust than a hardcoded ``parents[N]`` index: it works
    regardless of how deeply nested the test file is within the repository.
    """
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate repository root (no .git directory) starting from {start}"
    )


REPO_ROOT = _find_repo_root(Path(__file__).parent)
CONFIG_PATH = REPO_ROOT / ".coderabbit.yaml"



def config() -> dict:
    """Load and return the parsed .coderabbit.yaml as a plain dict."""
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# File-level sanity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_config_file_exists():
    assert CONFIG_PATH.exists(), f".coderabbit.yaml not found at {CONFIG_PATH}"


@pytest.mark.unit
def test_config_parses_as_valid_yaml():
    """The file must be syntactically valid YAML."""
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "Top-level YAML document must be a mapping"


# ---------------------------------------------------------------------------
# inheritance (new field)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_inheritance_enabled(config):
    """inheritance: true lets the org-level config layer underneath this file."""
    assert config.get("inheritance") is True


# ---------------------------------------------------------------------------
# reviews.auto_assign_reviewers (new field)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_auto_assign_reviewers_enabled(config):
    reviews = config["reviews"]
    assert reviews.get("auto_assign_reviewers") is True


# ---------------------------------------------------------------------------
# reviews.auto_review changes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_auto_review_drafts_is_true(config):
    """drafts was changed from false to true so feedback arrives before a PR is
    marked ready."""
    auto_review = config["reviews"]["auto_review"]
    assert auto_review.get("drafts") is True


@pytest.mark.unit
def test_auto_review_ignore_title_keywords_present(config):
    auto_review = config["reviews"]["auto_review"]
    keywords = auto_review.get("ignore_title_keywords")
    assert isinstance(keywords, list), "ignore_title_keywords must be a list"
    assert len(keywords) > 0, "ignore_title_keywords must not be empty"


@pytest.mark.unit
def test_auto_review_ignores_wip(config):
    keywords = config["reviews"]["auto_review"]["ignore_title_keywords"]
    assert "WIP" in keywords


@pytest.mark.unit
def test_auto_review_ignores_do_not_merge(config):
    keywords = config["reviews"]["auto_review"]["ignore_title_keywords"]
    assert "DO NOT MERGE" in keywords


@pytest.mark.unit
def test_auto_review_ignores_skip_ci(config):
    keywords = config["reviews"]["auto_review"]["ignore_title_keywords"]
    assert "[skip ci]" in keywords


@pytest.mark.unit
def test_auto_review_base_branches_unchanged(config):
    """The base_branches list must still contain 'main' after the PR."""
    base_branches = config["reviews"]["auto_review"]["base_branches"]
    assert "main" in base_branches


# ---------------------------------------------------------------------------
# reviews.finishing_touches (new section)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finishing_touches_simplify_enabled(config):
    finishing = config["reviews"].get("finishing_touches", {})
    assert finishing.get("simplify", {}).get("enabled") is True


# ---------------------------------------------------------------------------
# reviews.path_filters (new section)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_path_filters_is_list(config):
    path_filters = config["reviews"].get("path_filters")
    assert isinstance(path_filters, list), "path_filters must be a list"
    assert len(path_filters) > 0


@pytest.mark.unit
def test_path_filters_all_are_exclusions(config):
    """Every filter added in this PR is an exclusion (starts with '!')."""
    path_filters = config["reviews"]["path_filters"]
    for f in path_filters:
        assert f.startswith("!"), f"path_filter {f!r} must start with '!' to be an exclusion"


@pytest.mark.unit
def test_path_filters_excludes_package_lock(config):
    assert "!**/package-lock.json" in config["reviews"]["path_filters"]


@pytest.mark.unit
def test_path_filters_excludes_lock_files(config):
    assert "!**/*.lock" in config["reviews"]["path_filters"]


@pytest.mark.unit
def test_path_filters_excludes_dist(config):
    assert "!**/dist/**" in config["reviews"]["path_filters"]


@pytest.mark.unit
def test_path_filters_excludes_build(config):
    assert "!**/build/**" in config["reviews"]["path_filters"]


@pytest.mark.unit
def test_path_filters_excludes_coverage(config):
    path_filters = config["reviews"]["path_filters"]
    assert "!**/coverage/**" in path_filters
    assert "!**/htmlcov/**" in path_filters


@pytest.mark.unit
def test_path_filters_does_not_exclude_sdk_python(config):
    """sdk/python/** must NOT be in path_filters — it is intentionally kept
    in-scope so it stays in sync with backend models (per the comment in the
    file)."""
    path_filters = config["reviews"]["path_filters"]
    sdk_exclusions = [f for f in path_filters if "sdk/python" in f]
    assert sdk_exclusions == [], (
        "sdk/python must not be excluded from reviews; it must stay in sync "
        f"with backend models. Found exclusions: {sdk_exclusions}"
    )


# ---------------------------------------------------------------------------
# reviews.path_instructions — new entry for sdk/python/eventrelay_sdk/**
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def path_instructions(config) -> list:
    return config["reviews"].get("path_instructions", [])


@pytest.mark.unit
def test_sdk_python_path_instruction_exists(path_instructions):
    paths = [entry["path"] for entry in path_instructions]
    assert "sdk/python/eventrelay_sdk/**" in paths, (
        "Expected a path_instructions entry for 'sdk/python/eventrelay_sdk/**'"
    )


@pytest.mark.unit
def test_sdk_python_path_instruction_has_non_empty_instructions(path_instructions):
    entry = next(
        (e for e in path_instructions if e["path"] == "sdk/python/eventrelay_sdk/**"),
        None,
    )
    assert entry is not None
    instructions = entry.get("instructions", "").strip()
    assert instructions, "sdk/python/eventrelay_sdk/** instructions must not be empty"


@pytest.mark.unit
def test_sdk_python_path_instruction_mentions_sync(path_instructions):
    """Instructions should mention keeping the SDK in sync with backend models."""
    entry = next(
        (e for e in path_instructions if e["path"] == "sdk/python/eventrelay_sdk/**"),
        None,
    )
    assert entry is not None
    instructions = entry.get("instructions", "")
    assert "sync" in instructions.lower() or "models.py" in instructions, (
        "Path instructions for sdk/python/eventrelay_sdk/** should reference "
        "sync requirement with backend models"
    )


# ---------------------------------------------------------------------------
# reviews.tools.presidio (new tool)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_presidio_tool_enabled(config):
    tools = config["reviews"].get("tools", {})
    assert tools.get("presidio", {}).get("enabled") is True


# ---------------------------------------------------------------------------
# knowledge_base additions (linear, mcp)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_knowledge_base_linear_usage_enabled(config):
    kb = config.get("knowledge_base", {})
    assert kb.get("linear", {}).get("usage") == "enabled"


@pytest.mark.unit
def test_knowledge_base_mcp_usage_enabled(config):
    kb = config.get("knowledge_base", {})
    assert kb.get("mcp", {}).get("usage") == "enabled"


# ---------------------------------------------------------------------------
# issue_enrichment (entirely new section)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_issue_enrichment_section_exists(config):
    assert "issue_enrichment" in config, "issue_enrichment top-level key must exist"


@pytest.mark.unit
def test_issue_enrichment_auto_enrich_enabled(config):
    auto_enrich = config["issue_enrichment"].get("auto_enrich", {})
    assert auto_enrich.get("enabled") is True


@pytest.mark.unit
def test_issue_enrichment_labeling_auto_apply(config):
    labeling = config["issue_enrichment"].get("labeling", {})
    assert labeling.get("auto_apply_labels") is True


# ---------------------------------------------------------------------------
# Regression / boundary: pre-existing fields not broken by the PR
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_language_still_en_us(config):
    assert config.get("language") == "en-US"


@pytest.mark.unit
def test_early_access_still_true(config):
    assert config.get("early_access") is True


@pytest.mark.unit
def test_reviews_profile_still_assertive(config):
    assert config["reviews"].get("profile") == "assertive"


@pytest.mark.unit
def test_reviews_fail_commit_status_still_true(config):
    assert config["reviews"].get("fail_commit_status") is True


@pytest.mark.unit
def test_auto_review_still_enabled(config):
    assert config["reviews"]["auto_review"].get("enabled") is True


@pytest.mark.unit
def test_knowledge_base_learnings_scope_still_auto(config):
    assert config["knowledge_base"]["learnings"].get("scope") == "auto"
