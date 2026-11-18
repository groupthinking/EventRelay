# AHP client evaluation — November 18, 2026

Decision: **WATCH / isolated TEST**. This is a research recipe and fixture, not a product cut, architecture change, provider integration, new brand, or production dependency.

## Verified inputs
GitHub's [November 17 engineering announcement](https://github.blog/engineering/engineering-principles/building-the-agent-host-protocol-for-sessions-that-continue-across-devices/) describes cross-device session synchronization. Direct article retrieval failed; official indexed text was retrieved. Independent primary sources:
- [Published v1.1.0 release](https://github.com/microsoft/agent-host-protocol/releases/tag/v1.1.0), published November 13 00:24:30 UTC.
- [Pinned SDK README](https://github.com/microsoft/agent-host-protocol/blob/a501ea480fde1adc2675243039cb6195085f4b96/clients/typescript/README.md).
- [MIT license](https://github.com/microsoft/agent-host-protocol/blob/a501ea480fde1adc2675243039cb6195085f4b96/LICENSE).
- npm package @microsoft/agent-host-protocol@1.1.0 exists; registry integrity: sha512-6LXOqqXWGwMtrGxhIquNW9ECDPSHuW4yOpnIrOperBQuVZeRqbbmIGYn6ZZK3Q41/8heOi2LUlP9x9Wrsru3Eg==.

The installed library reports implementation version1.1.0 but advertises negotiation baselines **1.0.0 and0.9.0**. Use SUPPORTED_PROTOCOL_VERSIONS instead of copying the older README quickstart's0.3.0 or assuming the package version is negotiable.

AHP synchronizes session/display state; MCP supplies tool interaction. They are separate protocols. This does not establish identity, ownership or lineage with Hayden's MHS/MDS concepts; MDS remains undefined.

## Why it may matter
Inference: a future read-only companion could display a persistent agent session in a second UI while execution stays on its host. This is relevant to the existing interest in mobile interaction and agent orchestration. No proof that UVAI currently implements an AHP host, that an adapter fits its current contracts, or that this is an authorized product cut. Current authorized Origin G.A.T.E. work stays separate.

A candidate supervised deliverable is a cross-client session compatibility assessment for an agent team. Buyer demand, pricing, savings and revenue are hypotheses, not validated.

## Runnable no-provider recipe
Prerequisites: Node21+ (executed here on24.22.3), npm and public registry access. The SDK is MIT-licensed; this fixture needs no Copilot seat, provider key or model call. Real Copilot/cloud/provider use may require separate entitlements and costs; those are UNKNOWN here. Do not spend or change access settings.

1. Check out this research branch. Enter scripts/probes/ahp-watch-20261118.
2. Run `npm install --ignore-scripts --no-audit --no-fund`. This isolated manifest pins1.1.0; do not add it to root dependencies.
3. Run `npm test`. Expected three passing tests: advertised-version negotiation, surfaced unsupported-version error, and two mirrors converging after ordered replay while rejected actions do not change state.
4. Interpret the result narrowly. Counterpart messages and disconnect/replay sequence are fixtures using InMemoryTransport and published SDK code. No socket, real host, durable storage, mobile device, VS Code/Copilot interop, authentication boundary, or application task execution is proved.
5. Before any later adapter implementation, inspect current UVAI contracts and authorization; map task/approval identity, source version, rejection state and ordered replay without reinterpreting remote content as authority. Then validate on an already authorized host with two clients and real reconnect receipts. Host/client versions, policy/credential boundaries and price/access must be verified first. This is NOT RUN.

## Executed result
`npm install --prefix /tmp/ahp-watch-n18 --ignore-scripts --no-audit --no-fund @microsoft/agent-host-protocol@1.1.0` succeeded: one package installed.
`node --test /tmp/ahp-watch-n18/probe.test.mjs` exited0:3passed,0failed,0skipped. The committed source is the exact tested source.
An attempted additional `npm ci` was NOT RUN: the execution environment disconnected before process creation. Clean reinstall/lock reproducibility is not claimed. The initial install and the three actual test results remain valid dated evidence.
ESTIMATE:10minutes to reproduce the fixture;1–2days to scope a guarded adapter after actual host and contract evidence. No measured delivery-time reduction.

Rollback: remove only this isolated probe directory/branch when appropriate; no production setting or dependency has been changed. No PR was opened, no merge requested and no deployment performed.
Owner: Codex. Next trigger: an actual authorized AHP host and documented product need. Closure: independent two-client real-host session/reconnect trace, rejection/approval isolation and compatibility test evidence. Until then suppress an adoption/opportunity alert based only on these fixtures.


## Executed socket continuation — November 18
This adds evidence beyond the earlier in-memory-only checkpoint. `socket.test.mjs` uses Node TCP bound only to127.0.0.1 and the published SDK1.1.0 with a minimal synthetic JSON-RPC counterpart. Two client connections negotiate1.0.0, receive a shared action, then one disconnects. A third connection requests replay after serverSeq1. The test requires exactly one replayed action and asserts updated mirror state **before resubscription**, so a replacement snapshot cannot hide failed replay. A rejected third action preserves both mirrors.

Executed `node --test probe.test.mjs socket.test.mjs`:4passed,0failed,0skipped,exit0. Three TCP connections, one replayed action, one rejected action. Provider calls0; no real token, external host, application task or paid service. The server-side behavior remains synthetic; this is a real socket/SDK exchange, not production-host, browser/mobile, authorization-enforcement or persistence acceptance. The installed SDK and earlier recipe prerequisites remain unchanged.

The isolated manifest's `npm test` now includes both test files. `socket-result.json` retains this observed result. No root package, product architecture, workflow, PR, merge or deployment changed. Earlier dated limits stay preserved; only the statement that no socket was exercised is superseded by this bounded local experiment.
