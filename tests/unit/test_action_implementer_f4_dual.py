"""F4 — dual ActionImplementer resolution.

Canonical product agent: adapters.ActionImplementerAgent (registered name).
Offline batch helper: agents.action_implementer.ActionImplementer (not registered).
Shim re-exports the adapter class only.
"""

from __future__ import annotations

import warnings


def test_shim_exports_same_class_as_adapter():
    from youtube_extension.services.agents import action_implementer_agent as shim
    from youtube_extension.services.agents.adapters import (
        action_implementer_agent as adapter,
    )

    assert shim.ActionImplementerAgent is adapter.ActionImplementerAgent
    assert shim.ActionImplementerAgent.name == "action_implementer"


def test_offline_builder_is_not_the_agent():
    from agents.action_implementer import ActionImplementer
    from youtube_extension.services.agents.adapters.action_implementer_agent import (
        ActionImplementerAgent,
    )

    assert ActionImplementer is not ActionImplementerAgent
    assert getattr(ActionImplementer, "role", None) == "offline_plan_builder"
    assert ActionImplementerAgent.name == "action_implementer"


def test_offline_builder_warns_and_reexports_agent():
    from agents import action_implementer as offline_mod
    from youtube_extension.services.agents.adapters.action_implementer_agent import (
        ActionImplementerAgent as Canonical,
    )

    assert offline_mod.ActionImplementerAgent is Canonical

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        offline_mod.ActionImplementer()
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_registry_registers_adapter_once():
    # Importing the adapter module runs @register.
    from youtube_extension.services.agents.adapters.action_implementer_agent import (
        ActionImplementerAgent,
    )
    from youtube_extension.services.agents import registry as reg_mod

    registry = reg_mod._REG
    assert "action_implementer" in registry
    assert registry["action_implementer"] is ActionImplementerAgent
    # Single name → single class (no dual registration under aliases).
    aliases = [k for k, v in registry.items() if v is ActionImplementerAgent]
    assert aliases == ["action_implementer"]
