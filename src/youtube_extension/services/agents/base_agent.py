from .dto import AgentRequest, AgentResult


class BaseAgent:
    name = "base"

    def __init__(self, name: str | None = None, config: dict | None = None) -> None:
        if name:
            self.name = name
        self.config = config or {}

    def plan(self, req: AgentRequest) -> AgentResult:
        return AgentResult(status="ok", output={"plan": []})

    def run(self, req: AgentRequest) -> AgentResult:
        raise NotImplementedError

    def act(self, req: AgentRequest) -> AgentResult:
        # Optional: one-shot alias to run()
        return self.run(req)
