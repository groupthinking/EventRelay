"""Read-only, off-main live comparison canary. It does not run policy review."""
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from scripts.ci.record_dependency_review import record_dependency_review

PAIRS = {
    "control": (
        "3735132cdf6b0527630428cac3b24c9833f06d67",
        "222c0f05a3f28338a35298a035d5b2b0de55f6aa",
    ),
    "large": (
        "697581531dff8573ade650a9e7a0b4d5d6618301",
        "812ae9b00de9458ffaf1dfc68197c5b2d0a0e7dc",
    ),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(env, dest, opener):
    dest.mkdir(parents=True, exist_ok=False)
    token = env["GITHUB_TOKEN"]
    if not token:
        raise ValueError("Missing runner credential")
    base, head = env["BASE_SHA"], env["HEAD_SHA"]
    pair = f"{base}...{head}"
    paths = {f"/repos/groupthinking/EventRelay/dependency-graph/compare/{pair}"}
    paths.add(f"/repositories/1141250918/dependency-graph/compare/{pair}")
    pages = []
    receipt = {
        "base": base,
        "head": head,
        "runner_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "recorder_sha256": sha(Path("scripts/ci/record_dependency_review.py").read_bytes()),
        "run_id": env["GITHUB_RUN_ID"],
        "run_attempt": env["GITHUB_RUN_ATTEMPT"],
        "pages": pages,
        "status": "failed",
        "exit_code": 1,
    }

    def traced(request, timeout):
        url = urlsplit(request.full_url)
        if (url.scheme != "https" or url.netloc != "api.github.com"
                or url.path not in paths or token in request.full_url):
            raise ValueError("Request outside exact trusted comparison")
        if len(pages) >= 40:
            raise ValueError("Canary exceeded 40 pages")
        page = {"url": request.full_url, "status": None}
        pages.append(page)
        try:
            with opener(request, timeout=min(timeout, 15)) as response:
                raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise ValueError("Canary response exceeded size limit")
                headers = {
                    key: response.headers.get_all(key, [])
                    for key in ("Link", "x-github-dependency-graph-snapshot-warnings")
                }
                if token.encode() in raw or token in json.dumps([page, headers]):
                    raise ValueError("Credential-like data omitted")
                rows = json.loads(raw)
                filename = f"page-{len(pages):02}.json"
                (dest / filename).write_bytes(raw)
                page.update(status=response.status, headers=headers, file=filename,
                            sha256=sha(raw), rows=len(rows) if isinstance(rows, list) else None)
                body = io.BytesIO(raw)
                body.headers = response.headers
                return body
        except HTTPError as error:
            page["status"] = error.code
            raise ValueError(f"GitHub comparison HTTP {error.code}") from None

    try:
        result = record_dependency_review(env, dest / "recorded", opener=traced)
        diff = (dest / "recorded/dependency-diff.json").read_bytes()
        combined = []
        for page in pages:
            combined.extend(json.loads((dest / page["file"]).read_bytes()))
        if (sha(diff) != result["dependency_diff_sha256"]
                or len(combined) != result["dependency_diff_count"]
                or json.loads(diff) != combined):
            raise ValueError("Persisted comparison differs from captured pages")
        receipt.update(status="recorded", exit_code=0,
                       rows=len(combined), diff_sha256=sha(diff))
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}".replace(token, "[redacted]")[:400]
    finally:
        (dest / "trace.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    env = dict(os.environ, GITHUB_REPOSITORY="groupthinking/EventRelay",
               GITHUB_REPOSITORY_ID="1141250918", GITHUB_API_URL="https://api.github.com",
               REVIEW_OUTCOME="not_run")
    opener = build_opener(NoRedirect()).open
    summaries = {}
    for name, (base, head) in PAIRS.items():
        receipt = capture(dict(env, BASE_SHA=base, HEAD_SHA=head),
                          Path("dependency-trace-evidence") / name, opener)
        summaries[name] = (receipt["status"], len(receipt["pages"]), receipt.get("rows"))
        print(name, summaries[name])
    status, pages, _ = summaries["large"]
    return int(status != "recorded" or pages < 2)


if __name__ == "__main__":
    raise SystemExit(main())
