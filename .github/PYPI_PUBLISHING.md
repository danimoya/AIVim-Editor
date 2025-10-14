# PyPI Publishing Configuration Guide

## Overview
This repository is configured to automatically publish to PyPI when a new release is created. The workflow supports both traditional API token authentication and the more secure Trusted Publishing (OIDC) method.

## Table of Contents
- [Trusted Publishing Setup (Recommended)](#trusted-publishing-setup-recommended)
- [API Token Setup (Alternative)](#api-token-setup-alternative)
- [Creating a Release](#creating-a-release)
- [Testing with TestPyPI](#testing-with-testpypi)
- [Troubleshooting](#troubleshooting)

## Trusted Publishing Setup (Recommended)

Trusted Publishing uses OpenID Connect (OIDC) to authenticate with PyPI without storing long-lived API tokens. This is more secure and easier to manage.

### Prerequisites
- You must be a maintainer or owner of the PyPI project
- The repository must be public
- You need access to the PyPI project settings

### Setup Steps

1. **Go to your PyPI project settings**
   - Visit: https://pypi.org/manage/project/aivim/settings/
   - Or for a new project, you'll set this up during first publish

2. **Add a trusted publisher**
   - Navigate to "Publishing" → "Add a new pending publisher"
   - Fill in the following details:
     - **Owner**: `danimoya` (your GitHub username/org)
     - **Repository name**: `AIVim-Editor`
     - **Workflow name**: `publish-to-pypi.yml`
     - **Environment name**: `pypi` (optional but recommended)

3. **Save the configuration**
   - PyPI will now trust releases from this specific GitHub workflow

### Benefits of Trusted Publishing
- ✅ No API tokens to manage or rotate
- ✅ Automatic authentication via GitHub Actions
- ✅ More secure - tokens are short-lived and scoped
- ✅ Supports attestations for supply chain security

## API Token Setup (Alternative)

If you prefer to use API tokens or need them for specific scenarios:

### Generate PyPI API Token

1. **Log in to PyPI**
   - Visit: https://pypi.org/manage/account/

2. **Create an API token**
   - Go to "API tokens" → "Add API token"
   - Token name: `github-actions-aivim`
   - Scope: Select "Project: aivim" (or "Entire account" for first publish)
   - Click "Add token"

3. **Copy the token**
   - **IMPORTANT**: Copy the token immediately, you won't see it again!
   - The token starts with `pypi-`

### Add Token to GitHub Secrets

1. **Go to repository settings**
   - Navigate to: Settings → Secrets and variables → Actions

2. **Add new secret**
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Paste your PyPI token
   - Click "Add secret"

### For TestPyPI (Optional)

Repeat the same process for TestPyPI:
1. Generate token at: https://test.pypi.org/manage/account/
2. Add to GitHub as: `TEST_PYPI_API_TOKEN`

## Creating a Release

### Automatic Release Process

1. **Use the Release Automation Workflow**
   ```bash
   # Go to Actions → Automated Release Management
   # Click "Run workflow"
   # Select version bump type (patch/minor/major)
   ```

2. **The workflow will automatically:**
   - Bump the version in `pyproject.toml` and `VERSION`
   - Generate changelog from commits
   - Create and push a git tag
   - Create a GitHub release
   - Trigger PyPI publishing

### Manual Release Process

1. **Update version**
   ```bash
   # Edit pyproject.toml and VERSION file
   git add pyproject.toml VERSION
   git commit -m "chore: bump version to X.Y.Z"
   git push origin main
   ```

2. **Create a tag**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

3. **Create GitHub release**
   - Go to: https://github.com/danimoya/AIVim-Editor/releases/new
   - Choose the tag you just created
   - Generate release notes
   - Click "Publish release"

4. **PyPI publishing will trigger automatically**

## Testing with TestPyPI

Before publishing to production PyPI, you can test with TestPyPI:

1. **Manual trigger**
   - Go to: Actions → "Publish AIVim to PyPI"
   - Click "Run workflow"
   - Select environment: `testpypi`
   - Click "Run workflow"

2. **Verify package**
   ```bash
   # Install from TestPyPI
   pip install -i https://test.pypi.org/simple/ aivim

   # Test the package
   python -c "import aivim; print(aivim.__version__)"
   ```

## Workflow Features

### Security Features
- ✅ Attestations for supply chain security
- ✅ Security scanning with Bandit and Safety
- ✅ Dependency vulnerability checks
- ✅ SBOM (Software Bill of Materials) generation
- ✅ SHA256/SHA512 checksums for releases

### Quality Checks
- ✅ Tests on multiple Python versions (3.8-3.12)
- ✅ Cross-platform testing (Linux, macOS, Windows)
- ✅ Code quality checks (pylint, flake8, mypy)
- ✅ Package integrity verification
- ✅ Post-publish installation testing

### Environments
The workflow uses GitHub Environments for additional protection:
- **testpypi**: For test releases
- **pypi**: For production releases

You can add additional protection rules in:
Settings → Environments → [environment name] → Protection rules

## Troubleshooting

### Common Issues

#### 1. "No matching distribution found"
- **Cause**: Package not yet available on PyPI
- **Solution**: Wait 1-2 minutes after publish, PyPI needs time to index

#### 2. "Invalid or non-existent authentication"
- **Cause**: Missing or incorrect API token
- **Solution**: Verify `PYPI_API_TOKEN` secret is set correctly

#### 3. "Trusted publishing not configured"
- **Cause**: OIDC not set up on PyPI
- **Solution**: Follow Trusted Publishing setup steps above

#### 4. "Version already exists"
- **Cause**: Trying to upload same version twice
- **Solution**: Bump version number before releasing

#### 5. Build attestations failing
- **Cause**: Repository was private when configured
- **Solution**: Already fixed - attestations are now enabled

### Workflow Logs
- Check Actions tab for detailed logs
- Each job shows specific error messages
- Download artifacts for debugging

### Manual Publishing (Emergency)
If automated publishing fails:

```bash
# Build locally
python -m build

# Upload to PyPI
twine upload dist/*

# Or to TestPyPI
twine upload --repository testpypi dist/*
```

## Security Best Practices

1. **Use Trusted Publishing when possible**
   - More secure than API tokens
   - No tokens to leak or rotate

2. **If using API tokens:**
   - Use project-scoped tokens, not account-wide
   - Rotate tokens regularly
   - Never commit tokens to repository

3. **Enable branch protection**
   - Require pull request reviews
   - Require status checks to pass
   - Include administrators in restrictions

4. **Monitor releases**
   - Review release notes before publishing
   - Verify package contents
   - Test installation after publish

## Contact

For issues or questions:
- Create an issue: https://github.com/danimoya/AIVim-Editor/issues
- Email: daniel.moya@dimensigon.com

## References

- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [GitHub OIDC for PyPI](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Python Packaging Guide](https://packaging.python.org/)