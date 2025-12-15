# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing, building, and deployment.

## Coverage Workflow

**File:** `coverage.yml`

This workflow automatically generates and uploads code coverage reports to Qlty.

### Features:
- Runs on push to `main` and `develop` branches
- Runs on pull requests to `main` and `develop` branches
- Generates coverage reports in lcov format
- Uploads coverage to Qlty for tracking
- Stores coverage artifacts for 30 days

### Requirements:

1. **Python Dependencies**: Automatically installed via `pip install -e ".[dev]"`
2. **QLTY_COVERAGE_TOKEN**: Must be set as a repository secret

### Setting up QLTY_COVERAGE_TOKEN:

1. Get your coverage token from https://qlty.sh
2. Go to repository Settings → Secrets and variables → Actions
3. Add a new secret:
   - Name: `QLTY_COVERAGE_TOKEN`
   - Value: Your Qlty coverage token
4. Save the secret

### Workflow Stages:

1. **Checkout**: Checks out the repository code
2. **Setup Python**: Installs Python 3.12 with pip caching
3. **Install Dependencies**: Installs project dependencies including dev extras
4. **Create Reports Directory**: Ensures the reports directory exists
5. **Run Tests with Coverage**: Executes pytest with coverage reporting
6. **Upload to Qlty**: Sends coverage data to Qlty for tracking
7. **Upload Artifacts**: Stores coverage reports as GitHub artifacts

### Manual Trigger:

You can also run this workflow manually from the Actions tab in GitHub.

### Viewing Results:

- **GitHub Actions**: View workflow runs in the "Actions" tab
- **Coverage Reports**: Download artifacts from completed workflow runs
- **Qlty Dashboard**: View coverage trends at https://qlty.sh

## Adding More Workflows

To add additional workflows:

1. Create a new `.yml` file in this directory
2. Follow the GitHub Actions syntax
3. Define triggers, jobs, and steps
4. Test locally using `act` or similar tools
5. Commit and push to trigger the workflow

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Qlty Coverage Action](https://github.com/qltysh/qlty-action)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
