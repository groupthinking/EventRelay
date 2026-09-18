from pathlib import Path


def test_sprint_demo_agenda_labels_uvai_home_to_studio_evidence_and_fallbacks() -> None:
    agenda_path = Path(__file__).resolve().parents[2] / "docs" / "SPRINT_DEMO_AGENDA.md"
    agenda = agenda_path.read_text(encoding="utf-8")

    assert "# UVAI Home-to-Studio Sprint Demo Agenda" in agenda
    assert (
        "| Time | Owner | Demo action | Expected result | Evidence | Fallback |"
        in agenda
    )
    assert "This agenda does not authorize production deployment" in agenda
    assert "We are showing local or branch evidence only" in agenda
