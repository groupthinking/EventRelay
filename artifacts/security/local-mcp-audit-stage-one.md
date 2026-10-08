# Offline MCP audit: stage one

Implements the conservative inventory core of #2349. No launcher is executed,
environment value resolved, or network request made. Output omits raw arguments,
credential values, raw URLs, and untrusted metadata. Unknown provenance,
filesystem containment, and catalog capture remain null rather than invented.

Run from repository root:

```sh
python scripts/security/audit_local_mcp_configs.py --config .github/mcp-servers.json --config .gemini/settings.json --receipt /tmp/local-mcp-inventory.json
python -m pytest tests/security/test_local_mcp_config.py -q
```

The CLI deliberately exits 1 for BLOCKED or REVIEW_REQUIRED. This stage provides
no success/authorization path. Every local launcher requires containment review;
unsupported commands and npx modes fail closed. Containers, aliases and local
scripts remain blocked until dedicated parsers and reviewed policy exist.
Remote URLs require HTTPS and exclude credentials/query strings, but still need
review. This audit is not a complete secret scanner; do not submit secrets as
server names, configuration filenames or environment variable names.

The catalog helper hashes the complete recorded tool list plus server identity;
ordering of tools and object keys is normalized. Its output is evidence only,
not approval. Approval binding and invalidation integration remain unimplemented.

Remaining #2349 work: official publisher/version resolution, credential argv
migration, sandbox/filesystem/egress policy, complete container inventory, explicit
archive classification, approval integration, JSON Schema validation and CI
enforcement. Enabling enforcement before these launcher migrations would make
current main fail. This PR does not close #2349 or claim full remediation.

Verification: 19 fixture tests passed locally with sockets, DNS and subprocess
creation prohibited. Full repository checks and schema validation were not run.
Rollback: revert this commit. No production configuration is changed.
