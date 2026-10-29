"""Boundary for EventRelay's review-only AgentAction[] output.

This journals a local review artifact; it NEVER executes the original actions.
Existing Origin G.A.T.E. deploy receipts are neither consumed nor generalized.
"""

import json

from .core import ContractError, artifact_contract, text

REVIEW_TOOLS = frozenset(
    {
        "create_workflow_task",
        "save_resource",
        "schedule_followup",
        "dispatch_agent",
        "dispatch_subagents",
        "get_agent_session_logs",
        "add_to_knowledge_base",
    }
)


def prepare_review_artifact(key, actions, context=None):
    if not isinstance(actions, list) or not 0 <= len(actions) <= 100:
        raise ContractError("Expected 0..100 review-only AgentAction entries")
    clean = []
    for action in actions:
        if (
            not isinstance(action, dict)
            or not {"tool", "input", "status"} <= set(action)
            or set(action) - {"tool", "input", "status", "result", "isError"}
        ):
            raise ContractError("Invalid AgentAction shape")
        if (
            not isinstance(action["tool"], str)
            or action["tool"] not in REVIEW_TOOLS
            or action["status"] != "pending"
            or not isinstance(action["input"], dict)
        ):
            raise ContractError(
                "Only known pending review-only actions can be journaled"
            )
        if action.get("isError") not in (None, False):
            raise ContractError("Failed actions are not a review plan")
        if "result" in action:
            text(action["result"], "result")
        clean.append(
            {"tool": action["tool"], "input": action["input"], "status": "pending"}
        )
    body = {
        "source": "EventRelay review-only AgentAction[]",
        "original_actions_executed": False,
        "original_task_complete": False,
        "actions": clean,
        "next_step": "A trusted host must resolve user intent, permissions and a supported effect adapter before execution.",
    }
    content = json.dumps(body, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    return artifact_contract(
        key,
        "Persist an exact local review plan, not execute its actions",
        content,
        context=context,
        contains=['"original_actions_executed": false'],
    )
