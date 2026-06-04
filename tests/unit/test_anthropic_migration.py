"""Regression tests locking in the Claude model migration.

Guards the migrated Anthropic cost-table entries — the tier-preserving move to
Opus 4.8 / Sonnet 4.6 / Haiku 4.5 — which previously had no coverage. These
assertions import only the lightweight cost monitor, so they stay hermetic (no
provider SDK global config, no live calls).

Other parts of the migration are covered elsewhere: the SDK call sites
(output_config effort, no temperature) by the live smoke test, and the model-ID
swaps across the router/registries/enums by the migration's grep-clean check.
"""
import pytest

# Current tiers this codebase targets (no retired claude-3* IDs).
OPUS = "claude-opus-4-8"
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5"


def test_cost_monitor_lists_current_anthropic_tiers() -> None:
    from youtube_extension.backend.services.api_cost_monitor import APICostMonitor

    anthropic_models = APICostMonitor.COST_MODELS["anthropic"]
    # The current tiers must all be priced. The table may also retain historical
    # (retired) IDs so past usage logs can still be costed, so this is a subset
    # check rather than exact equality.
    assert {OPUS, SONNET, HAIKU} <= set(anthropic_models)


def test_cost_monitor_pricing_matches_published_tiers() -> None:
    from youtube_extension.backend.services.api_cost_monitor import APICostMonitor

    monitor = APICostMonitor(db_path=":memory:")
    # Pricing is per-1K tokens; 1000 in + 1000 out == input_rate + output_rate.
    assert monitor.calculate_cost("anthropic", OPUS, 1000, 1000) == pytest.approx(0.005 + 0.025)
    assert monitor.calculate_cost("anthropic", SONNET, 1000, 1000) == pytest.approx(0.003 + 0.015)
    assert monitor.calculate_cost("anthropic", HAIKU, 1000, 1000) == pytest.approx(0.001 + 0.005)
