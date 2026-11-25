# Image dependency remediation bootstrap

PR #2409 implements the bounded child [#2425](https://github.com/groupthinking/EventRelay/issues/2425).
The parent [#2396](https://github.com/groupthinking/EventRelay/issues/2396) remains
the unresolved image-security backlog. This is partial remediation; neither
scanner success nor a smaller report establishes a clean image or production
remediation.

## Bootstrap decision

Ship the already-verified application dependency repairs separately from final
strict Trivy enforcement. The required lowercase `trivy` job builds and scans
the exact PR source and retains image identity, source SHA and HIGH/CRITICAL
SARIF. Findings, including unfixed findings, are reported with `exit-code: '0'`.
Build and scanner execution failures still fail the job. No `continue-on-error`
is added to either scan, and the empty `.github/trivy-no-exceptions.txt` remains
the only ignore input. Existing `.trivyignore` IDs are not applied.

This is an explicit split, not a baseline-delta gate or accepted risk. It does
not block newly introduced findings. Review each new exact-image report before
merge; do not infer clearance from the scan-completion check. A future delta
gate would need separate review of advisory/package/version/path identity,
severity and occurrence regressions, missing/malformed evidence, and baseline
changes. A total-count cap alone is insufficient.

`limit-severities-for-sarif: true` fixes the review finding that the pinned action
otherwise clears `TRIVY_SEVERITY` for SARIF output. The historical SARIF files
below retain all originally generated results; future reports deliberately
honor the configured HIGH/CRITICAL threshold. See the
[pinned action implementation](https://github.com/aquasecurity/trivy-action/blob/ed142fd0673e97e23eac54620cfb913e5ce36c25/entrypoint.sh#L69-L76).

## Retained image evidence, inspected 2026-10-16

These are two historical snapshots. A new commit requires new hosted evidence.
Both images are linux/amd64; neither has a published `RepoDigest` in the retained
Docker inspect output. The following SHA256 values identify local image
contents, not registry publication.

| Field | Original retained scan | Latest inspected PR head |
| --- | --- | --- |
| Source commit | `1d9f72d7c40bff34aa43b8107cb817ad01e8efd5` | `64d2562dce7f2d870b32e3982ffe8888bbdcd808` |
| Run / job | [38258616455 / 114843053097](https://github.com/groupthinking/EventRelay/actions/runs/38258616455/job/114843053097) | [38706968204 / 116328658621](https://github.com/groupthinking/EventRelay/actions/runs/38706968204/job/116328658621) |
| Artifact ID | `11751896119` | `11958184738` |
| Image ID | `sha256:3e479db974698dc0bf11eec7fbce12acee901a33fe8179570fe4418a6b2ec34e` | `sha256:58c3934b3b50d5e9086a822bfd87f185839ff61f8302b0d165f1960acf839201` |
| HIGH / CRITICAL occurrences | **259** (258 / 1) | **252** (251 / 1) |
| OS / global npm / Python occurrences | 251 / 4 / 4 | 244 / 4 / 4 |
| Unique HIGH/CRITICAL advisories | 68 | 63 |
| All original SARIF results | 905 | 934 |

Artifact ZIP SHA256:

- Original: `545f1565a67c41fe5a9d641854e74f28bbb7050aa3247e537ca27d4fcb976459`.
- Latest inspected: `1ff1b9ca9a058b14f536a585bbe9e29e8dc0dbd3d079940878b0bd6422275217`.

Original `trivy-results.sarif` SHA256:

- Original: `3b32c283e60868c70b2929bc936d38c08e5f4f410d3e21ecad76ec10c95c9c37`.
- Latest inspected: `ebc2fa5c7bb192d8d523ed1395944cb2d2c3a780e905d9baf61763bfd67ed6f6`.

Both downloaded ZIPs were checked against provider artifact digests. Each
contains `image-source-commit.txt`, `image-identity.json` and the original
`trivy-results.sarif`; all original package paths and finding occurrences remain
in those artifacts. Local retained copies and occurrence-by-occurrence
reconciliation are under `work/pr2409-evidence/`, including
`scan-comparison.json`. Do not rewrite the 259-occurrence snapshot as a 252-row
baseline.

The source changes between these two heads are a merge from `main`; the image
Dockerfile, dependency inputs and scan workflow are unchanged. Seven
advisory/package/path occurrences disappeared from the later report:
`CVE-2026-8286` and `CVE-2026-8927` in curl/libcurl4t64,
`CVE-2026-88647` and `CVE-2026-88648` in libgnutls30t64, and
`CVE-2026-96889` in librsvg2-2. Curl/libcurl moved from
`8.14.1-2+deb13u5` to `8.14.1-2+deb13u7`; four continuing findings therefore
have changed version-bearing keys. Different image builds and scanner databases
can change reports. These disappearances are observations, not independently
accounted remediations.

## Remaining gates and ownership

All 244 OS occurrences in the latest inspected report have no fixed version
populated. The npm and pip vendor findings remain unresolved. Keep package
paths and runtime reachability in the #2396 ledger: application constraints
cannot replace private npm/pip vendor bundles, and removal of runtime tools is
a compatibility change requiring its own review.

Before closing #2425, obtain CI, Security Scan, Dependency Review, E2E, Coverage,
CodeQL, secret scan and applicable reviews for one exact implementation head.
Keep the PR draft while intentional required checks fail. The inspected
`64d2562…` head was open and **not** draft despite the stale description; it is
not evidence that these new changes passed hosted checks.

Before final strict enforcement, a re-fetched exact image or separately reviewed
applicability/VEX evidence must account for every remaining finding in #2396.
Enable `exit-code: '1'` with the same unfixed-finding and severity settings in a
separately reviewed change. Any exception needs the exact scope, applicability
evidence, owner, linked issue, compensating controls, expiry and enforced expiry
validation required by `MERGE_POLICY.md`. No merge, deployment, clean-image
claim or closure of #2396 follows from this bootstrap.

See [NumPy license investigation](numpy-license-review.md) for the independent
license gate. The license allowlist is unchanged.
