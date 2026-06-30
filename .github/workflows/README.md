# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing, building, and deployment.

## CodeQL Analysis Workflow

**File:** `codeql-analysis.yml`

This workflow performs static code analysis to detect security vulnerabilities and code quality issues using GitHub's CodeQL.

### Features:
- Runs on push to `main` branch
- Runs on pull requests to `main` branch
- Weekly scheduled analysis (Mondays at 6:00 AM UTC)
- Multi-language support with matrix strategy
- Analyzes JavaScript/TypeScript and Python code
- Uses custom configuration for path exclusions

### Languages Analyzed:
- **JavaScript/TypeScript**: Covers `.js`, `.jsx`, `.ts`, `.tsx` files
- **Python**: Covers `.py` files

### Configuration:
- Main workflow: `.github/workflows/codeql-analysis.yml`
- Configuration file: `.github/codeql/codeql-config.yml`
- Uses `security-and-quality` query suite for comprehensive analysis

### Workflow Stages:
1. **Checkout**: Checks out repository code with full history
2. **Initialize CodeQL**: Sets up CodeQL for each language in the matrix
3. **Autobuild**: Automatically builds the codebase
4. **Analyze**: Performs static analysis and uploads results

### Viewing Results:
- **Security Tab**: View detected vulnerabilities in the repository's Security tab
- **Pull Requests**: Analysis results appear as checks on PRs
- **Actions Tab**: View detailed workflow runs and logs

### Permissions Required:
- `contents: read` - To checkout repository
- `security-events: write` - To upload analysis results
- `actions: read` - To read workflow information

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

## Security Scan Workflow

**File:** `security.yml`

This workflow performs comprehensive security scanning using multiple tools to detect vulnerabilities in dependencies and code.

### Features:
- Runs on push to `main` branch
- Runs on pull requests to `main` branch
- Weekly scheduled scan (Sundays at midnight UTC)
- Multiple security tools for comprehensive coverage

### Security Tools:

1. **npm-audit**: Scans Node.js dependencies for known vulnerabilities
2. **python-safety**: Checks Python dependencies against safety database
3. **bandit**: Static analysis for Python code security issues
4. **trivy**: Container image vulnerability scanning

### Artifacts:
- npm audit reports
- Python safety reports
- Bandit security analysis reports

### Viewing Results:
- **Actions Tab**: View workflow runs and download security reports
- **Artifacts**: Download detailed security reports for each tool
- **Pull Requests**: Security checks appear on PRs

**Note**: CodeQL analysis has been moved to a dedicated workflow (`codeql-analysis.yml`) for better separation of concerns.

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
