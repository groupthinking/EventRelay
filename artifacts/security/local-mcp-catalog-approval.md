# Offline recorded MCP catalog approval

This is a bounded follow-up to #2349 / GRV-780. The launcher inventory remains
fail-closed and its catalog field remains null without trustworthy capture and
configuration binding. This comparator validates recorded evidence only. It
does not authorize a launcher, prove publisher identity, capture a live server,
or enforce active runtime configuration. The parent issue must remain open.

## Inputs and review boundary

A capture is strict JSON with exactly `identity` (a nonempty string) and
`response` (a complete recorded `tools/list` result containing `tools`). A
non-null `nextCursor` is rejected: callers must supply a complete, separately
assembled capture. Duplicate tool names, malformed fields, duplicate JSON keys
and nonfinite numbers fail closed. No MCP connection, subprocess, credential
lookup or environment expansion exists in the validator.

```sh
python scripts/security/validate_mcp_catalog.py --capture /tmp/capture.json
```

Exit 1 and `REVIEW_REQUIRED` are expected without an approval. The `observed`
object is a candidate pin with `approved: false`. A reviewer must inspect the
original identity and complete tools (including descriptions, schemas,
annotations and other metadata), separately store that object, and explicitly
set `approved: true` only after approval. There is no auto-approve command.
Pins are trusted reviewed files, not signatures or attestations. Protect them
with repository review/ownership policy; a party able to rewrite both the pin
and capture can bypass this comparison. Supplied identity is bound by hashing,
but independently establishing that identity and its active configuration is
still outstanding parent work. Do not commit actual active-server approvals
based on synthetic fixtures.

```sh
python scripts/security/validate_mcp_catalog.py --capture /tmp/capture.json --approval /tmp/reviewed-pin.json
python -m unittest discover -s tests/security -p test_mcp_catalog_approval.py -v
python -m pytest tests/security/test_local_mcp_config.py tests/security/test_mcp_catalog_approval.py -q -o addopts=''
```

Only an exact approved match exits 0 with `MATCH`. This means recorded-contract
equality, not permission to execute. Unapproved pins, changed identity, changed
catalogs, added/removed tools and inconsistent per-tool hashes block. Every tool
field participates in the original identity-bound full catalog digest. Tool
ordering and JSON object ordering are canonical; schema array ordering remains
significant. Hash algorithm/version is the existing Python SHA-256 canonical
JSON format, not a claim of cross-language RugSnare hash compatibility.

Separate schema (input/output) and description hashes explain drift. They never
relax the full-contract gate: description changes, hidden metadata and annotation
changes still invalidate approval. Output contains hashes and fixed status codes
only, never original names, identity, schemas, descriptions or exception text.
Treat source captures as sensitive; hashing is not encrypted storage.

## Reference evaluation

Inspected RugSnare commit `1551e5b28c5608a95fb1ad854c21191d8deabf81`:
`product/src/hash.js` splits structural/prose hashes, and `product/src/pins.js`
stores reviewed tool pins and detects NEW/REMOVED/DRIFT. The useful design is
diagnostic separation plus explicit pins. EventRelay retains its stronger
complete-tool/identity digest and rejects all drift. No RugSnare source is copied,
package installed, proxy adopted or runtime dependency added. Its live execution
paths are outside this offline implementation.

CI runs the dependency-free negative fixtures on every PR and main push, plus
the existing pytest inventory regressions in the Python matrix. This is a
regression gate for the comparator, not active-catalog enforcement: there are no
approved real captures in this change. Remaining parent work includes provenance,
credential migration, containment, trustworthy capture/configuration binding and
active-configuration CI/runtime enforcement. Roll back by reverting this change;
no production MCP configuration is modified.
