# Triage — non-required `trivy` and `Vercel` failures (2026-08-25)

Triage artifact for GRV-428. Covers the two non-required red signals observed on
the root-cleanliness evidence head (PR
[#1558](https://github.com/groupthinking/EventRelay/pull/1558), commit
`4305c159`). Both are triaged separately below. Neither invalidates the
root-cleanliness evidence and neither blocks Phase 2: branch protection does not
require either check (see `MERGE_POLICY.md` — the six security checks, `trivy`
included, are not in the required set, and `Vercel` is an external commit
status).

## 1. `trivy` job (security.yml) — Docker build regression, not a vulnerability

**Symptom.** The `trivy` job fails with
`unable to find the specified image "eventrelay:test"`.

**Root cause.** The failure is upstream of Trivy itself. The job's
"Build image for scanning" step (`docker build -t eventrelay:test .`) fails
during `npm ci --workspace=apps/web --production --legacy-peer-deps`:

```
npm error command sh -c node scripts/patch-world-vercel-undici-fetch.mjs
npm error Error: Cannot find module '/app/apps/web/scripts/patch-world-vercel-undici-fetch.mjs'
```

`apps/web/package.json` gained a `postinstall` hook running
`scripts/patch-world-vercel-undici-fetch.mjs` (the #1538 WDK undici-fetch fix,
PR #1545), but the Dockerfile builder stage copied only
`apps/web/package.json` before `npm ci` — the scripts directory only arrived in
the final `COPY . .` of the runtime stage. So the builder-stage install has been
failing ever since. With the build failed, the first Trivy step is skipped, the
SARIF upload errors (`Path does not exist: trivy-results.sarif`), and the
`if: always()` table-report step is what actually fails the job — it invokes
`trivy image eventrelay:test` against an image that was never built.

**Timeline.** `security.yml` was green through 2026-08-13T18:55Z (run
31733235574) and has failed on every run since 2026-08-13T19:01Z (run
31733775769, branch `fix/wdk-patch-world-vercel-fetch-1538`) — the exact commit
window that introduced the postinstall hook. The failure is deterministic and
branch-independent (fails identically on `main`, PR branches, and Dependabot
branches), which is itself evidence it carries no signal about any particular
PR's content.

**Severity classification.** CI infrastructure defect. No vulnerability
finding is involved — Trivy never scanned anything (both scan steps run with
`exit-code: '0'` anyway, so even findings would not fail the job).

**Remediation (in this PR).** Copy `apps/web/scripts` into the builder stage
before `npm ci`. The patch script is idempotent and exits cleanly when the
target package is absent, so it is safe at image-build time.

## 2. `Vercel` commit status — dashboard-side cancellation, external to the repo

**Symptom.** Commit status `Vercel` reports `failure` with description
"Canceled from the Vercel Dashboard", target
`vercel.com/garv1/v0-uvai/H3kq8SwapLbvGs6ms62f1bQ8vaLs`.

**Root cause.** The `v0-uvai` Vercel project (a v0-generated app connected to
this repository) had its preview deployment for the PR head cancelled from the
Vercel dashboard. This is an operator/dashboard action on an auxiliary project,
not a build or code failure. The authoritative signal for this repo,
`Vercel Deployments – garv_projects`, reported `success` on the same head with
"No required projects to validate", and the in-repo Vercel check runs
(`Vercel Preview Comments`, `Vercel Agent Review`) both passed.

**Severity classification.** Informational. Nothing in the repository causes or
can fix it; a cancelled auxiliary preview deploy carries no signal about the
change under review.

**Remediation (dashboard, optional).** In the Vercel dashboard, either
disconnect the `v0-uvai` project from this repository or add an ignored-build
step so it does not post commit statuses for changes that don't touch it. No
repo change required or possible.

## Why neither blocks Phase 2

- Neither check is in the required set (`MERGE_POLICY.md` gate analysis;
  branch protection requires neither `trivy` nor the `Vercel` status).
- The `trivy` red is a deterministic Dockerfile/CI defect that predates and is
  orthogonal to the root-cleanliness work; the `Vercel` red is an external
  dashboard cancellation on an auxiliary project.
- All required checks on the evidence head passed, so the root-cleanliness
  evidence in PR #1558 stands as recorded.
