from pathlib import Path


PERSONA_MAP = (
    Path(__file__).parents[2] / ".github" / "copilot-personas.md"
)


def test_copilot_persona_map_covers_primary_conversation_context() -> None:
    content = PERSONA_MAP.read_text()

    assert "# Copilot User Persona Map" in content
    for persona in (
        "The Builder",
        "The Product/Technical Founder",
        "The Automation or Operations Lead",
        "The Educator or Researcher",
        "The Enterprise Engineering Team",
        "The EventRelay Contributor",
    ):
        assert f"## {persona}" in content
