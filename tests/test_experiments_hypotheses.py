"""Smoke tests for the hypothesis experiment scaffold."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from experiments import HYPOTHESIS_IDS, run_hypothesis
from experiments.retrieval_lab import RetrievalDocument, RetrievalLab


def test_hypothesis_ids_are_present() -> None:
    assert HYPOTHESIS_IDS == ("h1", "h2", "h3")


def test_all_hypotheses_can_run() -> None:
    for hypothesis_id in HYPOTHESIS_IDS:
        result = run_hypothesis(hypothesis_id, context={"dataset": "demo"})
        assert result["hypothesis"] == hypothesis_id
        assert result["status"] == "ready"
        assert result["agent"]["hypothesis"] == hypothesis_id


def test_retrieval_lab_can_index_and_query() -> None:
    lab = RetrievalLab(
        [
            RetrievalDocument(
                document_id="doc-1",
                content="The retrieval lab measures precision on grounded evidence.",
                metadata={"type": "grounded"},
            ),
            RetrievalDocument(
                document_id="doc-2",
                content="Structured summaries help the agent maintain context through execution.",
                metadata={"type": "summary"},
            ),
        ]
    )
    result = lab.validate("grounded evidence")
    assert result["match_count"] >= 1
    assert result["matches"][0]["id"] == "doc-1"
