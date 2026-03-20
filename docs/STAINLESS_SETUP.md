# Stainless SDK Setup Guide

This guide walks you through setting up Stainless SDK generation for EventRelay.

## Prerequisites

1. **Stainless Account**: Sign up at [stainless.com](https://www.stainless.com)
2. **GitHub Account**: For CI/CD integration
3. **npm/PyPI Accounts**: For publishing SDKs

## Step 1: Install Stainless CLI

```bash
npm install -g stainless
```

## Step 2: Authenticate with Stainless

```bash
stainless login
```

This will open a browser window for authentication.

## Step 3: Verify OpenAPI Spec

Ensure your OpenAPI specification is valid:

```bash
# Generate the spec
python scripts/generate_openapi.py

# Validate it
npx @apidevtools/swagger-cli validate openapi.yaml
```

## Step 4: Configure Stainless

The `.stainless.yaml` configuration file defines SDK generation settings:

```yaml
organization: groupthinking
project: eventrelay

spec:
  path: ./openapi.yaml
  version: 3.1.0

sdks:
  python:
    package_name: eventrelay
    output_dir: ./sdks/python
  typescript:
    package_name: "@groupthinking/eventrelay"
    output_dir: ./sdks/typescript
```

## Step 5: Generate SDKs Locally

### Python SDK

```bash
stainless generate \
  --language python \
  --output ./sdks/python \
  --spec openapi.yaml
```

### TypeScript SDK

```bash
stainless generate \
  --language typescript \
  --output ./sdks/typescript \
  --spec openapi.yaml
```

## Step 6: Test Generated SDKs

### Python

```bash
cd sdks/python
pip install -e ".[dev]"
pytest tests/ -v
```

### TypeScript

```bash
cd sdks/typescript
npm install
npm test
npm run build
```

## Step 7: Configure GitHub Actions

### Required Secrets

Add these secrets to your GitHub repository:

1. **STAINLESS_API_KEY**
   - Get from Stainless dashboard
   - Settings → Secrets → New repository secret

2. **NPM_TOKEN** (for npm publishing)
   - Generate at npmjs.com/settings/tokens
   - Select "Automation" token type

3. **PyPI Publishing** (uses OIDC, no token needed)
   - Configure trusted publisher at pypi.org
   - Project → Settings → Publishing
   - Add GitHub Actions publisher:
     - Owner: groupthinking
     - Repository: EventRelay
     - Workflow: stainless-sdk.yml
     - Environment: pypi

### Workflow File

The workflow is at `.github/workflows/stainless-sdk.yml`.

It runs on:
- Push to `main` when OpenAPI spec changes
- Manual workflow dispatch
- Release publication

## Step 8: Setup Package Publishing

### Python (PyPI)

1. Create PyPI account at pypi.org
2. Configure trusted publisher (OIDC - no token needed)
3. Package details:
   - Name: `eventrelay-sdk`
   - Owner: groupthinking
   - Workflow: `stainless-sdk.yml`
   - Environment: `pypi`

### TypeScript (npm)

1. Create npm account at npmjs.com
2. Join `@groupthinking` organization (or create it)
3. Generate automation token
4. Add `NPM_TOKEN` secret to GitHub

## Step 9: Initial SDK Release

### Manual Generation

```bash
# 1. Generate OpenAPI spec
python scripts/generate_openapi.py

# 2. Generate SDKs
stainless generate --language python --output ./sdks/python
stainless generate --language typescript --output ./sdks/typescript

# 3. Test SDKs
cd sdks/python && pip install -e ".[dev]" && pytest tests/
cd ../typescript && npm install && npm test && npm run build

# 4. Publish manually (first release)
cd ../python && python -m build && python -m twine upload dist/*
cd ../typescript && npm publish --access public
```

### Automated via GitHub Actions

```bash
# Trigger workflow manually
gh workflow run stainless-sdk.yml -f publish=true

# Or create a release
git tag v1.0.0
git push origin v1.0.0
gh release create v1.0.0 --generate-notes
```

## Step 10: Continuous Updates

### Automatic SDK Regeneration

The GitHub Actions workflow automatically:

1. **Detects OpenAPI changes** (on push to main)
2. **Validates spec** using swagger-cli
3. **Generates SDKs** via Stainless
4. **Runs tests** on generated code
5. **Creates PR** with updated SDKs
6. **Publishes** on release (if triggered)

### Manual SDK Update

```bash
# 1. Update FastAPI routes/models
# 2. Regenerate OpenAPI spec
python scripts/generate_openapi.py

# 3. Commit and push
git add openapi.yaml
git commit -m "feat: update OpenAPI spec with new endpoints"
git push origin main

# 4. Workflow auto-generates SDKs and creates PR
```

## Troubleshooting

### OpenAPI Validation Errors

```bash
# Check for errors
npx @apidevtools/swagger-cli validate openapi.yaml

# Common fixes:
# - Ensure all Pydantic models have proper type hints
# - Add response_model to all FastAPI endpoints
# - Use Enum for status fields
```

### SDK Generation Fails

```bash
# Check Stainless config
stainless validate-config

# Check spec compatibility
stainless check-spec openapi.yaml

# View detailed logs
stainless generate --verbose
```

### GitHub Actions Workflow Fails

1. Check workflow logs in GitHub Actions tab
2. Verify secrets are set correctly
3. Ensure STAINLESS_API_KEY is valid
4. Check npm/PyPI credentials

### SDK Tests Fail

```bash
# Python
cd sdks/python
pip install -e ".[dev]"
pytest tests/ -vv --tb=short

# TypeScript
cd sdks/typescript
npm install
npm test -- --verbose
```

## Best Practices

### 1. Keep OpenAPI Spec Updated

Always regenerate after API changes:

```bash
python scripts/generate_openapi.py
```

### 2. Version SDKs Properly

Follow semantic versioning:
- **Major** (2.0.0): Breaking changes
- **Minor** (1.1.0): New features
- **Patch** (1.0.1): Bug fixes

### 3. Test Before Publishing

```bash
# Run full test suite
cd sdks/python && pytest tests/ -v
cd ../typescript && npm test
```

### 4. Document API Changes

Add release notes when publishing:

```bash
gh release create v1.1.0 \
  --title "SDK v1.1.0 - New Events API" \
  --notes "Added support for event filtering and webhooks"
```

### 5. Monitor SDK Usage

Track downloads:
- PyPI: https://pypistats.org/packages/eventrelay-sdk
- npm: https://npmtrends.com/@groupthinking/eventrelay

## Resources

- [Stainless Documentation](https://www.stainless.com/docs)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- [GitHub Actions](https://docs.github.com/actions)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [npm Automation Tokens](https://docs.npmjs.com/creating-and-viewing-access-tokens)

## Support

- **Issues**: [GitHub Issues](https://github.com/groupthinking/EventRelay/issues)
- **Discussions**: [GitHub Discussions](https://github.com/groupthinking/EventRelay/discussions)
- **Stainless Support**: support@stainless.com
- **Email**: team@uvai.com
