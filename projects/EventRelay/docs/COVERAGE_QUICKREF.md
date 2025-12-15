# Quick Reference: Coverage Reporting

## Generate Coverage Locally

```bash
# Quick test with coverage
pytest tests/unit/ --cov=src/youtube_extension --cov-report=lcov:reports/lcov.info --cov-report=term

# Full test suite with all reports
pytest tests/ \
  --cov=src/youtube_extension \
  --cov-report=lcov:reports/lcov.info \
  --cov-report=term \
  --cov-report=html:reports/htmlcov
```

## View Coverage Reports

```bash
# Open HTML coverage report in browser
open reports/htmlcov/index.html  # macOS
xdg-open reports/htmlcov/index.html  # Linux
```

## GitHub Actions Setup

1. **Get Qlty Token**: Log in to https://qlty.sh → Project Settings → Coverage → Copy Token
2. **Add to GitHub**: Repository Settings → Secrets and variables → Actions → New secret
   - Name: `QLTY_COVERAGE_TOKEN`
   - Value: Your token
3. **Verify**: Push code or create PR → Check Actions tab → Coverage should upload automatically

## Monitoring Scripts

```bash
# Quick coverage (unit tests only)
./development/monitoring/run_coverage_report.sh --quick

# Detailed coverage (all tests)
./development/monitoring/run_coverage_report.sh --detailed

# CI mode (machine-readable)
./development/monitoring/run_coverage_report.sh --ci
```

## Coverage Standards

- **Minimum**: 80% coverage
- **Target**: 90%+ coverage
- **Production Gate**: 85%+ for deployment

## File Locations

- **Config**: `pyproject.toml` → `[tool.coverage.lcov]`
- **Workflow**: `.github/workflows/coverage.yml`
- **Reports**: `reports/lcov.info` and `reports/htmlcov/`
- **Documentation**: `docs/COVERAGE_SETUP.md`

## Troubleshooting

### No coverage data collected
```bash
# Install dependencies
pip install pytest pytest-cov coverage

# Verify installation
python -m coverage --version
```

### Token not working
- Check secret name is exactly `QLTY_COVERAGE_TOKEN`
- Verify token hasn't expired in Qlty dashboard
- Check workflow logs for authentication errors

### Low coverage warnings
- Review `reports/htmlcov/index.html` for uncovered lines
- Add tests for critical code paths
- Use `# pragma: no cover` for untestable code

## Related Documentation

- [Full Setup Guide](./COVERAGE_SETUP.md)
- [GitHub Workflows](../.github/workflows/README.md)
- [Testing Guide](./guides/ENHANCED_README.md#running-tests)
