"""Exercise pagination failures without forwarding credentials or saving partial data."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from scripts.ci.record_dependency_review import record_dependency_review

ENV = {
    "BASE_SHA": "a" * 40,
    "HEAD_SHA": "b" * 40,
    "GITHUB_REPOSITORY": "groupthinking/EventRelay",
    "GITHUB_TOKEN": "test-pagination-token",
    "GITHUB_RUN_ID": "123",
    "GITHUB_RUN_ATTEMPT": "1",
    "REVIEW_OUTCOME": "success",
}
URL = (
    "https://api.github.com/repos/groupthinking/EventRelay/dependency-graph/compare/"
    + "a" * 40
    + "..."
    + "b" * 40
)


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(json.dumps(body).encode())
        self.headers = headers or {}


@pytest.mark.parametrize(
    "next_url",
    [
        "https://example.invalid/collect-token?page=2",
        URL.replace("https://", "http://") + "?page=2",
        URL.replace("/compare/", "/other/") + "?page=2",
        URL + "?page=2#fragment",
    ],
)
def test_untrusted_next_link_is_rejected_before_request(tmp_path: Path, next_url: str):
    requested = []

    def opener(request, timeout):
        requested.append(request.full_url)
        assert request.full_url == URL, "Authentication must not reach another endpoint"
        return Response([], {"Link": f'<{next_url}>; rel="next"'})

    with pytest.raises(ValueError, match="pagination"):
        record_dependency_review(
            ENV, tmp_path / "evidence", opener=opener, changed_files=set()
        )
    assert requested == [URL]
    assert not (tmp_path / "evidence").exists()


def test_cyclic_next_link_is_rejected_without_repeating_request(tmp_path: Path):
    requested = []

    def opener(request, timeout):
        requested.append(request.full_url)
        assert len(requested) <= 2, "A repeated pagination URL must not be opened"
        next_url = URL + "?page=2" if len(requested) == 1 else URL
        return Response([], {"Link": f'<{next_url}>; rel="next"'})

    with pytest.raises(ValueError, match="pagination"):
        record_dependency_review(
            ENV, tmp_path / "evidence", opener=opener, changed_files=set()
        )
    assert requested == [URL, URL + "?page=2"]
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize(
    "last_page,headers,error",
    [
        (
            [],
            {"x-github-dependency-graph-snapshot-warnings": "incomplete"},
            "snapshot warnings",
        ),
        ({"unexpected": "object"}, {}, "complete change list"),
        (["not a change"], {}, "complete change list"),
    ],
)
def test_later_page_failure_never_saves_partial_evidence(
    tmp_path, last_page, headers, error
):
    pages = iter(
        [
            Response(
                [{"manifest": "requirements.txt", "name": "alpha"}],
                {"Link": f'<{URL}?page=2>; rel="next"'},
            ),
            Response(last_page, headers),
        ]
    )
    with pytest.raises(ValueError, match=error):
        record_dependency_review(
            ENV,
            tmp_path / "evidence",
            opener=lambda *args, **kwargs: next(pages),
            changed_files={"requirements.txt"},
        )
    assert not (tmp_path / "evidence").exists()


def test_relative_next_link_and_relation_list_preserve_complete_evidence(tmp_path):
    requested = []
    changes = [
        {"manifest": "requirements.txt", "name": name} for name in ("alpha", "beta")
    ]

    def opener(request, timeout):
        requested.append(request.full_url)
        assert request.get_header("Authorization") == "Bearer test-pagination-token"
        if request.full_url == URL:
            return Response(
                changes[:1],
                {"Link": '<?page=2>; type="application/json"; rel="next last"'},
            )
        assert request.full_url == URL + "?page=2"
        return Response(changes[1:])

    dest = tmp_path / "evidence"
    result = record_dependency_review(
        ENV, dest, opener=opener, changed_files={"requirements.txt"}
    )
    raw = (dest / "dependency-diff.json").read_bytes()
    assert requested == [URL, URL + "?page=2"]
    assert json.loads(raw) == changes
    assert result["dependency_diff_count"] == 2
    assert result["dependency_diff_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize(
    "link",
    [
        '<broken; rel="next"',
        '<?page=2>; rel="next", <?page=3>; rel="next"',
        '<?page=2>; rel="next"; rel="last"',
    ],
)
def test_malformed_or_ambiguous_pagination_cannot_save_success(tmp_path, link):
    with pytest.raises(ValueError, match="pagination"):
        record_dependency_review(
            ENV,
            tmp_path / "evidence",
            opener=lambda *args, **kwargs: Response([], {"Link": link}),
            changed_files=set(),
        )
    assert not (tmp_path / "evidence").exists()


def test_page_budget_rejects_unbounded_unique_links(tmp_path, monkeypatch):
    from scripts.ci import record_dependency_review as module

    monkeypatch.setattr(module, "MAX_COMPARE_PAGES", 2)
    requested = []

    def opener(request, timeout):
        requested.append(request.full_url)
        return Response([], {"Link": f'<?page={len(requested) + 1}>; rel="next"'})

    with pytest.raises(ValueError, match="pagination"):
        record_dependency_review(
            ENV, tmp_path / "evidence", opener=opener, changed_files=set()
        )
    assert requested == [URL, URL + "?page=2"]
    assert not (tmp_path / "evidence").exists()


def test_quoted_parameter_content_is_not_a_pagination_relation(tmp_path):
    result = record_dependency_review(
        ENV,
        tmp_path / "evidence",
        opener=lambda *args, **kwargs: Response(
            [], {"Link": '<?page=2>; type="example; rel=next"; rel="last"'}
        ),
        changed_files=set(),
    )
    assert result["dependency_diff_count"] == 0


def test_reordered_query_does_not_bypass_cycle_detection(tmp_path):
    requested = []

    def opener(request, timeout):
        requested.append(request.full_url)
        assert len(requested) <= 2
        target = "?page=2&per_page=30" if len(requested) == 1 else "?per_page=30&page=2"
        return Response([], {"Link": f'<{target}>; rel="next"'})

    with pytest.raises(ValueError, match="pagination"):
        record_dependency_review(
            ENV, tmp_path / "evidence", opener=opener, changed_files=set()
        )
    assert len(requested) == 2
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize(
    "api_root", ["https://api.github.com", "https://github.example.invalid/api/v3"]
)
def test_trusted_repository_id_route_keeps_pagination_working(tmp_path, api_root):
    environment = {**ENV, "GITHUB_REPOSITORY_ID": "12345", "GITHUB_API_URL": api_root}
    initial = URL.replace("https://api.github.com", api_root)
    canonical = (
        initial.replace("repos/groupthinking/EventRelay", "repositories/12345")
        + "?page=2"
    )
    requested = []

    def opener(request, timeout):
        requested.append(request.full_url)
        if len(requested) == 1:
            return Response([], {"Link": f'<{canonical}>; rel="next"'})
        assert request.full_url == canonical
        return Response([])

    record_dependency_review(
        environment, tmp_path / "evidence", opener=opener, changed_files=set()
    )
    assert requested == [initial, canonical]


def test_different_repository_id_is_rejected_before_request(tmp_path):
    environment = {**ENV, "GITHUB_REPOSITORY_ID": "12345"}
    bad = (
        URL.replace("repos/groupthinking/EventRelay", "repositories/67890") + "?page=2"
    )
    requested = []

    def opener(request, timeout):
        requested.append(request.full_url)
        assert len(requested) == 1
        return Response([], {"Link": f'<{bad}>; rel="next"'})

    with pytest.raises(ValueError, match="pagination"):
        record_dependency_review(
            environment, tmp_path / "evidence", opener=opener, changed_files=set()
        )
    assert requested == [URL]
    assert not (tmp_path / "evidence").exists()
