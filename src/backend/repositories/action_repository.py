class ActionRepository:
    """Test stub shim for ActionRepository used in integration tests.
    This provides a minimal in-memory implementation compatible with the tests' patched methods.
    """
    _actions = {}

    def get_by_video_id(self, video_id: str):
        return [a for a in self._actions.values() if a.get("video_id") == video_id]

    def update(self, action_id: str, **kwargs):
        action = self._actions.get(action_id)
        if not action:
            return None
        action.update(kwargs)
        self._actions[action_id] = action
        return action

    def save(self, action: dict):
        action_id = action.get("id") or f"action_{len(self._actions)+1}"
        action["id"] = action_id
        self._actions[action_id] = action
        return action
