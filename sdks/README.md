# EventRelay SDKs

This folder contains multi-language SDKs generated from the EventRelay FastAPI OpenAPI schema.

- `openapi/eventrelay.openapi.json` is produced via `python scripts/export_openapi.py`.
- `stainless.config.ts` wires the OpenAPI spec into Stainless for SDK generation.
- `sdks/typescript` provides a TypeScript client package.
- `sdks/python` provides a Python client package.

## Generate with Stainless

```bash
python scripts/export_openapi.py
npx stainless generate --config stainless.config.ts
```

## Publish

- **Python**: `cd sdks/python && python -m build && twine upload dist/*`
- **TypeScript**: `cd sdks/typescript && npm run build && npm publish`
