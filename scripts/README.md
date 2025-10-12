# Scripts Directory

This directory contains utility scripts for managing the AIVim Editor project.

## Version Management

### bump_version.py

Automated version management script that ensures consistency across all version references.

#### Usage

```bash
# Bump patch version (0.5.1 -> 0.5.2)
python scripts/bump_version.py patch

# Bump minor version (0.5.1 -> 0.6.0)
python scripts/bump_version.py minor

# Bump major version (0.5.1 -> 1.0.0)
python scripts/bump_version.py major

# Set specific version
python scripts/bump_version.py 1.2.3

# Validate version consistency
python scripts/bump_version.py --validate

# Dry run (show what would change)
python scripts/bump_version.py patch --dry-run
```

#### What it does

The script updates version numbers in:
- `VERSION` file
- `pyproject.toml`
- `aivim/__init__.py` (if `__version__` exists)

#### Release Workflow

1. Bump the version:
   ```bash
   python scripts/bump_version.py minor
   ```

2. Review and commit changes:
   ```bash
   git add VERSION pyproject.toml aivim/__init__.py
   git commit -m "Bump version to 0.6.0"
   ```

3. Create and push tag:
   ```bash
   git tag v0.6.0
   git push origin main --tags
   ```

4. Create a GitHub release (triggers PyPI publishing)

## CI/CD Setup

The project includes comprehensive CI/CD workflows in `.github/workflows/`:

### test.yml
- Runs on every PR and push to main/develop
- Multi-platform testing (Ubuntu, macOS, Windows)
- Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
- Code quality checks (flake8, black, isort, mypy, pylint)
- Security scanning (bandit, safety)
- Coverage reporting

### security.yml
- Runs daily and on every PR/push
- Multiple security scanners:
  - Bandit (Python security)
  - Safety (dependency vulnerabilities)
  - CodeQL (advanced analysis)
  - TruffleHog (secret detection)
  - Semgrep (pattern-based security)
  - OSSF Scorecard (project health)
- License compliance checking

### publish-to-pypi.yml
- Triggers on GitHub releases or manual dispatch
- Pre-publish security and quality checks
- Supports TestPyPI and PyPI publishing
- Post-publish validation
- Automatic GitHub release asset upload

## Development Tools

### Pre-commit Hooks

Install pre-commit hooks for automated code quality checks:

```bash
pip install pre-commit
pre-commit install
```

Run manually on all files:
```bash
pre-commit run --all-files
```

### Security Scanning

Run security checks locally:

```bash
# Install security tools
pip install bandit safety

# Run bandit
bandit -r aivim -ll -i

# Check dependencies
safety check
```

### Code Quality

Run code quality tools:

```bash
# Install tools
pip install black isort flake8 mypy pylint

# Format code
black aivim tests
isort aivim tests

# Lint code
flake8 aivim
mypy aivim
pylint aivim
```

### Testing

Run tests with coverage:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=aivim --cov-report=html

# Run specific test file
pytest tests/test_editor.py

# Run tests in parallel
pytest -n auto
```

## Configuration Files

The project includes several configuration files in the root directory:

- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.bandit` - Bandit security scanner settings
- `.flake8` - Flake8 linting configuration
- `.pylintrc` - Pylint configuration
- `pyproject.toml` - Project metadata and tool configurations
- `MANIFEST.in` - Package distribution file inclusions

## GitHub Secrets

The following secrets need to be configured in GitHub repository settings:

### Required for PyPI Publishing
- `PYPI_API_TOKEN` - PyPI API token for production releases
- `TEST_PYPI_API_TOKEN` - TestPyPI API token for test releases

### Setup Instructions

1. Generate PyPI API tokens:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token with scope for the project
   - Go to https://test.pypi.org/manage/account/token/ for TestPyPI

2. Add secrets to GitHub:
   - Go to repository Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Add `PYPI_API_TOKEN` and `TEST_PYPI_API_TOKEN`

## Continuous Integration

### Pull Request Workflow

When you create a PR:
1. Test suite runs on all supported platforms and Python versions
2. Code quality checks are performed
3. Security scans are executed
4. Dependency review checks for vulnerabilities
5. Coverage reports are generated

### Release Workflow

To create a new release:
1. Bump version using `bump_version.py`
2. Commit and push changes
3. Create a GitHub release with tag `vX.Y.Z`
4. GitHub Actions automatically:
   - Runs pre-publish checks
   - Builds distribution packages
   - Publishes to PyPI
   - Validates installation
   - Uploads assets to GitHub release

### Manual Publishing

You can manually trigger publishing:

```bash
# Via GitHub UI: Actions > Publish AIVim to PyPI > Run workflow
# Select environment: testpypi or pypi
```

## Troubleshooting

### Version Mismatch

If versions are inconsistent:
```bash
python scripts/bump_version.py --validate
```

### Failed Tests

Check test output and run locally:
```bash
pytest -v --tb=short
```

### Security Issues

Review security scan reports in GitHub Actions artifacts.

### Build Failures

Validate the build locally:
```bash
pip install build twine
python -m build
twine check dist/*
```
