# Coverage Reporting Configuration

This document explains how to set up coverage reporting with Qlty for the EventRelay project.

## Overview

EventRelay uses Coverage.py to generate coverage data in lcov format, which is then uploaded to Qlty for tracking and reporting.

## Setup Instructions

### 1. Generate Coverage Data Locally

Coverage data is generated automatically when running tests with the coverage flag:

```bash
# Run tests with coverage
pytest tests/ \
  --cov=src/youtube_extension \
  --cov-report=lcov:reports/lcov.info \
  --cov-report=term \
  --cov-report=html:reports/htmlcov
```

The lcov format output will be saved to `reports/lcov.info`.

### 2. Configure Coverage Settings

Coverage settings are configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/youtube_extension"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "src/youtube_extension/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]

[tool.coverage.lcov]
output = "reports/lcov.info"
```

### 3. GitHub Actions Configuration

The `.github/workflows/coverage.yml` workflow automatically:
- Runs tests with coverage on push/PR
- Generates lcov format reports
- Uploads coverage data to Qlty
- Stores coverage artifacts for 30 days

### 4. Setting Up QLTY_COVERAGE_TOKEN

To enable coverage uploads to Qlty, you need to configure the `QLTY_COVERAGE_TOKEN` secret in your GitHub repository:

#### Steps:

1. **Get your Qlty Coverage Token:**
   - Log in to your Qlty account at https://qlty.sh
   - Navigate to your project settings
   - Go to the "Coverage" section
   - Copy your coverage token

2. **Add the token to GitHub Secrets:**
   - Go to your GitHub repository
   - Click on "Settings" → "Secrets and variables" → "Actions"
   - Click "New repository secret"
   - Name: `QLTY_COVERAGE_TOKEN`
   - Value: Paste your Qlty coverage token
   - Click "Add secret"

3. **Verify the configuration:**
   - Push a commit or create a PR
   - Check the "Actions" tab to see the coverage workflow run
   - Coverage data should be uploaded to Qlty automatically

## Usage

### Running Coverage Locally

```bash
# Quick coverage report (unit tests only)
./development/monitoring/run_coverage_report.sh --quick

# Detailed coverage report (all test suites)
./development/monitoring/run_coverage_report.sh --detailed

# CI mode (machine-readable output)
./development/monitoring/run_coverage_report.sh --ci
```

### Viewing Coverage Reports

#### Local HTML Report
After running tests with coverage, open `reports/htmlcov/index.html` in your browser to view the detailed coverage report.

#### Qlty Dashboard
View coverage trends and metrics in your Qlty project dashboard at https://qlty.sh

## Coverage Standards

EventRelay maintains high code quality standards:
- **Minimum Coverage**: 80%
- **Target Coverage**: 90%+
- **Production Readiness Gate**: 85%+ for all components

## Troubleshooting

### Coverage Token Not Working
- Verify the token is correctly set in GitHub Secrets
- Check that the secret name is exactly `QLTY_COVERAGE_TOKEN`
- Ensure your Qlty account has access to the repository

### No Coverage Data Generated
- Verify pytest-cov is installed: `pip install pytest-cov`
- Check that tests are running successfully
- Ensure the `reports/` directory exists and is writable

### Low Coverage Warnings
- Review uncovered code in the HTML report
- Add tests for critical paths
- Use `# pragma: no cover` for code that cannot be tested

## References

- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Qlty Coverage Documentation](https://qlty.sh/docs/coverage)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
