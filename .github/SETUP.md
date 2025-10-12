# GitHub Repository Setup Guide

This guide walks you through setting up the AIVim Editor repository for automated CI/CD and PyPI publishing.

## Prerequisites

- Repository admin access
- PyPI account (https://pypi.org)
- TestPyPI account (https://test.pypi.org)

## Step 1: PyPI Configuration

### 1.1 Create PyPI API Tokens

#### For Production PyPI

1. Log in to https://pypi.org
2. Go to Account Settings > API tokens
3. Click "Add API token"
4. Token name: `aivim-github-actions`
5. Scope: Select "Project: aivim" (after first manual upload) or "Entire account"
6. Click "Add token"
7. **Important**: Copy the token immediately (starts with `pypi-`)

#### For TestPyPI

1. Log in to https://test.pypi.org
2. Follow the same steps as above
3. Token name: `aivim-github-actions-test`
4. Copy the token (starts with `pypi-`)

### 1.2 First Upload to PyPI (One-time)

If this is the first time publishing the package:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

After the first upload, you can scope the API token to the specific project.

## Step 2: Configure GitHub Secrets

### 2.1 Add Repository Secrets

1. Go to your GitHub repository
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**

Add the following secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `PYPI_API_TOKEN` | `pypi-...` | Production PyPI API token |
| `TEST_PYPI_API_TOKEN` | `pypi-...` | TestPyPI API token |

### 2.2 Configure Environments (Optional)

For additional security, configure deployment environments:

1. Go to **Settings** > **Environments**
2. Create two environments:
   - `pypi` (for production)
   - `testpypi` (for testing)
3. For `pypi` environment, add protection rules:
   - Required reviewers: Add yourself/team
   - Wait timer: 0 minutes (or set as needed)
4. Add environment secrets if you prefer environment-scoped tokens

## Step 3: Enable GitHub Actions

### 3.1 Verify Workflows

1. Go to **Actions** tab
2. Verify the following workflows are present:
   - Test Suite
   - Security Scanning
   - Publish AIVim to PyPI

### 3.2 Configure Workflow Permissions

1. Go to **Settings** > **Actions** > **General**
2. Under "Workflow permissions":
   - Select "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"
3. Click **Save**

## Step 4: Security Setup

### 4.1 Enable Dependabot

1. Go to **Settings** > **Code security and analysis**
2. Enable:
   - Dependency graph
   - Dependabot alerts
   - Dependabot security updates
   - Dependabot version updates

### 4.2 Create Dependabot Configuration

File is already created at `.github/dependabot.yml`

### 4.3 Enable CodeQL

CodeQL is automatically enabled through the security workflow. Verify:

1. Go to **Security** > **Code scanning**
2. Verify CodeQL scans are running

### 4.4 Configure Branch Protection

1. Go to **Settings** > **Branches**
2. Add rule for `main` branch:
   - Require a pull request before merging
   - Require status checks to pass before merging
     - Select: Test Suite
     - Select: Security Scanning
   - Require conversation resolution before merging
   - Require signed commits (optional but recommended)
3. Click **Create** or **Save changes**

## Step 5: Pre-commit Hooks (Local Development)

For contributors to set up local pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# (Optional) Run against all files
pre-commit run --all-files
```

## Step 6: Test the Setup

### 6.1 Test PR Workflow

1. Create a test branch
2. Make a small change
3. Create a pull request
4. Verify:
   - Tests run on multiple platforms
   - Security scans complete
   - Code quality checks pass

### 6.2 Test Release Workflow (TestPyPI)

1. Ensure you're on the main branch
2. Run version bump:
   ```bash
   python scripts/bump_version.py patch
   ```
3. Commit changes:
   ```bash
   git add VERSION pyproject.toml
   git commit -m "Bump version for test release"
   git push
   ```
4. Go to **Actions** > **Publish AIVim to PyPI**
5. Click **Run workflow**
6. Select `testpypi` environment
7. Click **Run workflow**
8. Verify:
   - Pre-publish checks pass
   - Build succeeds
   - Package is published to TestPyPI
   - Can install: `pip install -i https://test.pypi.org/simple/ aivim`

### 6.3 Test Production Release

1. Bump version:
   ```bash
   python scripts/bump_version.py minor
   ```
2. Commit and push
3. Create a GitHub release:
   - Go to **Releases** > **Create a new release**
   - Tag version: `v0.6.0` (match the version)
   - Release title: `AIVim v0.6.0`
   - Description: Add release notes
   - Click **Publish release**
4. Verify:
   - Publish workflow triggers automatically
   - Package is published to PyPI
   - Can install: `pip install aivim`
   - Release assets are uploaded

## Step 7: Documentation

### 7.1 Update Repository Description

1. Go to repository main page
2. Click the gear icon next to **About**
3. Add:
   - Description: "AI-enhanced Vim-like text editor with code assistance"
   - Website: Link to documentation or PyPI
   - Topics: `python`, `editor`, `ai`, `vim`, `terminal`

### 7.2 Add Badges to README

Add status badges to your README.md:

```markdown
[![Test Suite](https://github.com/danimoya/AIVim-Editor/actions/workflows/test.yml/badge.svg)](https://github.com/danimoya/AIVim-Editor/actions/workflows/test.yml)
[![Security Scanning](https://github.com/danimoya/AIVim-Editor/actions/workflows/security.yml/badge.svg)](https://github.com/danimoya/AIVim-Editor/actions/workflows/security.yml)
[![PyPI version](https://badge.fury.io/py/aivim.svg)](https://badge.fury.io/py/aivim)
[![Python Versions](https://img.shields.io/pypi/pyversions/aivim.svg)](https://pypi.org/project/aivim/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

## Troubleshooting

### Publishing Fails with Authentication Error

- Verify secrets are correctly set
- Check token hasn't expired
- Ensure token has correct scope

### Security Scans Failing

- Review security scan reports in Actions artifacts
- Some failures are expected and can be reviewed
- Set `continue-on-error: true` for non-critical checks

### Tests Failing on Specific Platform

- Review test logs
- May need platform-specific fixes
- Can exclude specific platforms if necessary

### Version Mismatch Error

```bash
# Validate and fix version consistency
python scripts/bump_version.py --validate
python scripts/bump_version.py <current_version>
```

## Maintenance

### Regular Tasks

1. **Weekly**: Review Dependabot PRs
2. **Monthly**: Check security scan results
3. **Quarterly**: Review and update dependencies
4. **As needed**: Bump version and create releases

### Security Monitoring

- Monitor GitHub Security alerts
- Review CodeQL findings
- Keep dependencies up to date
- Rotate API tokens periodically (every 6-12 months)

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Publishing Guide](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Security Best Practices](https://docs.github.com/en/code-security)
- [Pre-commit Documentation](https://pre-commit.com/)

## Support

For issues or questions:
- Open an issue in the repository
- Check existing discussions
- Review GitHub Actions logs for detailed error messages
