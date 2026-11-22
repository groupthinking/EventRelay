# Evidence-bound video reconstruction

Tracked by [#2798](https://github.com/groupthinking/EventRelay/issues/2798). This additive local path implements the UVAI → EventRelay integration authorized by Hayden on November 22, 2026. It consumes an existing UVAI Video Pack; it does not initiate another extraction or change the public Studio.

## What is being reconstructed

The first source is [Google AI Studio's multimodal powers](https://www.youtube.com/watch?v=auJzb1D-fag), using the retained real pack at `apps/web/src/lib/sample-pack/auJzb1D-fag.pack.json`. Its demonstrated flows inform an original browser interface with three supported capabilities:

| Capability | Source requirement | Local behavior | Limit |
|---|---|---|---|
| YouTube attachment | `G-REQ-01` | Validate and save a YouTube URL as a removable media attachment | No video ingestion, thumbnail fetch, or token counting |
| Structured summary | `G-REQ-02` | Validate and render explicitly imported structured summary data | No model inference or fabricated response |
| Bounding-box view | `G-REQ-03` | Display a local image and explicitly supplied normalized boxes; toggle labels and inspect the coordinates | No automatic object detection |

These are scoped browser acceptance criteria. Passing them does not pass the original source's end-to-end acceptance, which includes unavailable live backend behavior. Original required blockers are retained. An illustrative sample, where present, is labeled as sample data and cannot become source observation or model-run evidence.

## Reusable specification

The execution contract separates four kinds of information:

| Section | Producer | Required evidence | Meaning |
|---|---|---|---|
| Observed evidence | Source assessor | Source identity, exact raw pack digest, validated citation rows and timestamps | Source-linked material. A model's visual description remains a model description. |
| Inferred architecture | Architect | Explicit requirement mappings, rationale and a trusted renderer profile | Chosen implementation approach; not an observation from the video. |
| Generated code | Builder | Exact file paths, byte lengths, hashes and builder identity | Files exist with specified contents; that alone does not establish behavior. |
| Verified functionality | Independent local verifier | Actual browser checks bound to the same source, profile, generated files and run | Only the named tested browser behaviors. Failed, missing or mismatched evidence cannot pass. |

An identity hash is not a content hash. The existing Video Pack `source_hash` identifies the video. The reconstruction also hashes the exact pack bytes and recomputes the canonical grounded-spec review digest. Changing source text, citations, requirements or limitations invalidates the previous binding.

The profile is explicit operator-authored data. It maps source requirement IDs to a fixed registry of supported browser capabilities. Unknown capabilities fail rather than executing video-supplied code or guessing an app from its title. Another tutorial can use the same contract and verification path when its source supports those capabilities. Other application types require a reviewed renderer and meaningful behavior checks; this version is not a general-purpose autonomous app compiler.

The contract implementation is `scripts/video-reconstruction/contract.ts`. Its JSON Schema projection describes structural validation; `loadSource`, `readProfile`, `parseManifest`, `verifyFiles`, and `finalizeManifest` additionally enforce citation, digest, path, and run consistency. Validating JSON against the schema alone never establishes executed functionality.

### Agent responsibilities

| Role | Instruction | Output | Completion rule |
|---|---|---|---|
| Source assessor | Inspect source material, identify citation/provenance gaps, and preserve contradictions | Source-linked evidence and limitations | Exact source artifacts are available; unsupported observations are flagged |
| Architect | Map supported source requirements to trusted browser capabilities and identify excluded backend behavior | Bound profile and scoped acceptance | Every mapping has valid source support and an explicit rationale |
| Builder | Emit the supported app using the trusted renderer; treat source strings as data | Hashed generated files | All expected files are present and no unexpected path is introduced |
| Verifier | Exercise the real generated app, including failure cases and responsive/theme states | Browser receipt and visual-review material | Named checks ran successfully against those exact files |
| EventRelay executor | Persist the exact final manifest through the existing local harness | Current durable local artifact receipt | The actual stored bytes still match the contract |

These roles can be assigned to separate agents or executed sequentially. A builder cannot upgrade its own generated claim into verified behavior. The executable runner invokes the verifier itself; it does not accept a caller-supplied success receipt as execution authority.

## EventRelay boundary

The adapter uses the existing `scripts/relay_harness` command journal and its fixed `write_local_artifact` tool. Source content cannot select an executable, filesystem destination, adapter, credential, or authority. The adapter submits a contract, runs it, then reads the current receipt back. Its idempotency identity includes the exact content it persists.

A `relay.local-receipt.v1` proves only the local artifact effect. It is not an Origin G.A.T.E. decision, deployment authorization, or evidence that a live model ran. A changed/deleted artifact invalidates completion. The trusted local operator owns the runner code and state directory; local hashes and the journal are not remote attestation against that operator.

## Source-review correction

The retained Video Pack's visual rows at 360, 400 and 455 seconds describe app screens. The packaged JPEGs at those timestamps are the same presenter poster image, so they cannot independently verify those descriptions. Publisher storyboard frames recovered directly from the YouTube player show the attachment, summary and spatial flows, but are low-resolution samples at five-second intervals. They support workflow inspection, not pixel-exact reconstruction or precise validation of the pack's transcript timing. In particular, the publisher frame at 400 seconds shows the Build gallery, while the pack's visual description calls it a summary screen.

The immutable input is preserved. This discrepancy belongs in provenance and review evidence; silently rewriting the input or treating duplicate poster frames as independently verified screenshots would hide it.

Source review on November 22, 2026 established the following bindings:

| Artifact | SHA-256 |
|---|---|
| Retained repository pack, exact bytes | `6e3ba3035f4b98e229198ce471d9c24ff88783879ab253725bc381f92be646ee` |
| Live UVAI HTTP 200 response, exact bytes | `df64c4cc0fcb718e34bd8b68b17aa5b9b71ecff62dc481f9fade5dd95d31a179` |
| Canonical grounded review, recomputed for both | `e86e5b3383a64cc4508b4d5681a4c3e6e3aafe0c64473cf796e88cb8c82ea40c` |
| Duplicate poster at 360/400/455 seconds | `bfc51208f4dba3369c919c2ff2a874d2c49efa05d4038230c6425b9feb594e10` |

The live and retained packs parsed to the same JSON content. Their exact byte hashes differ, so a run must retain the digest of the actual input it used. The source endpoint was `https://uvai.io/api/video/pack?video_id=auJzb1D-fag`; the retained copy was checked at repository commit `b771cd1546d4071514ae136739632bf726c343a1`. The video publisher is Google Cloud Tech. Publisher storyboard review used 320×180 tiles at five-second intervals; transient player URLs and cookies are not part of the committed record.

## Execute and verify

Use a Linux checkout with the repository dependencies installed, Node 24, Python 3, and a supported Chromium installation. The generated browser app itself has no build dependencies. The local command journal requires the existing Python standard-library runtime. No model credentials are needed for this scoped reconstruction.

Install the workspace Playwright browser and recorder from the repository root.

```bash
npm exec --workspace apps/web -- playwright install --with-deps chromium
```

This installs Playwright’s Chromium build, its system dependencies, and the FFmpeg binary used to record browser sessions. Playwright requires its FFmpeg binary even when the runner uses a system Chromium executable.

Run the reconstruction commands from the repository root.

```bash
node --import tsx scripts/video-reconstruction/cli.ts run --out /tmp/uvai-reconstruction
node --import tsx scripts/video-reconstruction/cli.ts verify --out /tmp/uvai-reconstruction
node --import tsx scripts/video-reconstruction/cli.ts schema
```

`run` requires a fresh absolute output directory. It emits the app, checks its actual browser behavior, and only then persists the finalized manifest through EventRelay. `verify` checks an existing run against current input bytes, regenerated code, captured evidence and the current durable artifact. It does not rerun a model or treat an imported success flag as authority. Use the same `--source` and `--profile` inputs on both commands when overriding the retained defaults.

`RECONSTRUCTION_CHROMIUM` can select an installed browser using a trusted absolute executable path. The runner otherwise uses the local or bundled Chromium. A blocked launch or failed check exits nonzero and leaves unverified failure evidence. It cannot create a successful browser receipt or completed relay effect by skipping the browser.

The output contains the generated app under `app/` and run evidence under `evidence/`. The pending manifest and browser-run identity are recorded before verification. The capture inventory, browser receipt, finalized manifest and exact EventRelay receipt are staged together under `evidence/partial/`, checked against actual files and relay state, then published atomically under `evidence/verified/`. Replay accepts the published directory only and rejects any run containing `failure.json`.

A late publication failure preserves any actual append-only journal write and records the relay effect as `not_attempted`, `unconfirmed` or `persisted`. Partial evidence stays separate from the canonical success files. A failed overall run is never described as successful, and a completed local write is never falsely described as unexecuted.

Screenshots and continuous recordings cover both screens at 720×900, 1440×900 and 1920×1080 in light and dark mode. Capture bytes are part of replay validation. Moving a run to another host does not turn an archived local receipt into a current receipt on that host.

### Regression checks

```bash
npm exec -- tsc -p scripts/video-reconstruction/tsconfig.json
node --import tsx --test tests/video-reconstruction*.test.ts
python3 -m unittest discover -s tests -p test_relay_local_harness.py -v
```

The [reconstruction workflow](../.github/workflows/video-reconstruction.yml) runs these checks and a real sample reconstruction on the exact pull-request head. It retains the app, receipts, screenshots and recordings as a GitHub Actions artifact. This workflow uses no model or production credentials. It does not replace the repository's other required checks or authorize a merge.

## Operational limits

No local test makes the full original app, live inference, token accounting, visual parity, hosting or production deployment verified. The existing G.A.T.E. contract, extractor provider, pack store and public product behavior remain separate. The old App Builder workspace still exports source evidence and SOPs; it is not relabeled as a reconstructed app.

Run evidence must identify its exact source and files. Historical test counts and another machine's receipts do not establish current completion. Revalidate current files and the current EventRelay artifact before relying on a saved run.
