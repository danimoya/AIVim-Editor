# Release Process Guide

This guide explains how to create and publish new releases of AIVim.

## Table of Contents
- [Pre-Release Checklist](#pre-release-checklist)
- [Automated Release](#automated-release-recommended)
- [Manual Release](#manual-release-alternative)
- [Post-Release](#post-release)
- [Hotfix Releases](#hotfix-releases)

## Pre-Release Checklist

Before creating a release, ensure:

- [ ] All tests pass on main branch
- [ ] Documentation is up to date
- [ ] CHANGELOG.md reflects changes
- [ ] No security vulnerabilities in dependencies
- [ ] Version numbers are consistent across files

### Run Pre-Release Checks
```bash
# Run full test suite
pytest tests/ -v

# Security scan
bandit -r aivim
safety check

# Build test
python -m build
twine check dist/*

# Clean up
rm -rf dist/ build/ *.egg-info
```

## Automated Release (Recommended)

### Using GitHub Actions

1. **Navigate to Actions**
   - Go to: https://github.com/danimoya/AIVim-Editor/actions
   - Select "Automated Release Management"

2. **Configure Release**
   - Click "Run workflow"
   - Select branch: `main`
   - Choose version bump:
     - `patch`: Bug fixes (0.5.4 → 0.5.5)
     - `minor`: New features (0.5.4 → 0.6.0)
     - `major`: Breaking changes (0.5.4 → 1.0.0)
   - Pre-release: Check if this is a beta/alpha
   - Draft: Check to review before publishing

3. **Review and Confirm**
   - Click "Run workflow"
   - Monitor progress in Actions tab

4. **What Happens Automatically**
   - Version bumped in `pyproject.toml` and `VERSION`
   - Changelog generated from commits
   - Git tag created and pushed
   - GitHub release created
   - Package built and published to PyPI
   - Attestations generated for security

## Manual Release (Alternative)

### 1. Update Version

```bash
# Update version in pyproject.toml
sed -i 's/version = "X.Y.Z"/version = "X.Y.Z+1"/' pyproject.toml

# Update VERSION file
echo "X.Y.Z+1" > VERSION

# Update CHANGELOG.md
# Add new version section with date and changes
```

### 2. Commit Changes

```bash
git add pyproject.toml VERSION CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"
git push origin main
```

### 3. Create Tag

```bash
# Create annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z

Summary of changes:
- Feature: ...
- Fix: ...
- Enhancement: ..."

# Push tag
git push origin vX.Y.Z
```

### 4. Create GitHub Release

1. Go to: https://github.com/danimoya/AIVim-Editor/releases/new
2. Select the tag: `vX.Y.Z`
3. Title: `vX.Y.Z`
4. Generate release notes automatically
5. Add any additional notes
6. Attach any additional files if needed
7. Check "Pre-release" if applicable
8. Click "Publish release"

### 5. Publishing Triggers Automatically

Once the release is published, GitHub Actions will:
- Build the package
- Run security checks
- Publish to PyPI with attestations
- Upload artifacts to the release

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

1.2.3
│ │ └── Patch: Bug fixes, minor updates
│ └──── Minor: New features, backwards compatible
└────── Major: Breaking changes
```

### Examples:
- Bug fix: `0.5.4` → `0.5.5`
- New feature: `0.5.4` → `0.6.0`
- Breaking change: `0.5.4` → `1.0.0`
- Pre-release: `1.0.0-alpha.1`, `1.0.0-beta.1`, `1.0.0-rc.1`

## Testing Releases

### Test with TestPyPI First

1. **Trigger Test Release**
   ```bash
   # Go to Actions → "Publish AIVim to PyPI"
   # Run workflow → Select "testpypi"
   ```

2. **Install and Test**
   ```bash
   pip install -i https://test.pypi.org/simple/ aivim==X.Y.Z
   aivim --version
   ```

3. **Verify Package Contents**
   ```bash
   # Download package
   pip download -i https://test.pypi.org/simple/ aivim==X.Y.Z

   # Inspect wheel
   unzip -l aivim-X.Y.Z-py3-none-any.whl

   # Inspect tarball
   tar -tzf aivim-X.Y.Z.tar.gz
   ```

## Post-Release

### Verify Release

1. **Check PyPI**
   - Visit: https://pypi.org/project/aivim/
   - Verify version is live
   - Check package description

2. **Test Installation**
   ```bash
   # Create fresh virtual environment
   python -m venv test-env
   source test-env/bin/activate  # or test-env\Scripts\activate on Windows

   # Install from PyPI
   pip install aivim==X.Y.Z

   # Test it works
   aivim --version
   aivim --help
   ```

3. **Check GitHub Release**
   - Verify assets are attached
   - Check release notes
   - Ensure tag is correct

### Announce Release

1. **Update Documentation**
   - Update installation instructions if needed
   - Update compatibility notes

2. **Notify Users** (if applicable)
   - Create announcement issue
   - Update project board
   - Social media if relevant

## Hotfix Releases

For urgent fixes:

1. **Create hotfix branch**
   ```bash
   git checkout -b hotfix/X.Y.Z+1 vX.Y.Z
   ```

2. **Apply fix**
   ```bash
   # Make changes
   git add .
   git commit -m "fix: critical bug in ..."
   ```

3. **Fast-track release**
   ```bash
   # Update version
   # Update CHANGELOG
   git add pyproject.toml VERSION CHANGELOG.md
   git commit -m "chore: bump version to X.Y.Z+1"

   # Push and tag
   git push origin hotfix/X.Y.Z+1
   git tag -a vX.Y.Z+1 -m "Hotfix vX.Y.Z+1"
   git push origin vX.Y.Z+1
   ```

4. **Create release**
   - Mark as pre-release initially
   - Test thoroughly
   - Remove pre-release flag when confirmed

5. **Merge back**
   ```bash
   # Merge to main
   git checkout main
   git merge hotfix/X.Y.Z+1
   git push origin main

   # Delete hotfix branch
   git branch -d hotfix/X.Y.Z+1
   git push origin --delete hotfix/X.Y.Z+1
   ```

## Rollback Procedure

If a release has issues:

### 1. Yank from PyPI (if critical)
```bash
# Mark version as yanked on PyPI
# This prevents new installations but doesn't break existing
# Go to: https://pypi.org/manage/project/aivim/release/X.Y.Z/
# Click "Options" → "Yank"
```

### 2. Create Fix
- Follow hotfix procedure above
- Clearly document the issue in CHANGELOG

### 3. Re-release
- Use next patch version
- Reference the yanked version in notes

## Troubleshooting

### Common Issues

#### Build Fails
```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info
python -m build
```

#### Version Mismatch
```bash
# Ensure versions match
grep version pyproject.toml
cat VERSION
git tag -l | tail -1
```

#### PyPI Upload Fails
- Check API token is valid
- Verify you have upload permissions
- Ensure version doesn't already exist

#### Tests Fail in CI
- Check if it's environment-specific
- Run locally with same Python version
- Review recent dependency updates

## Workflow Status

Monitor workflow runs:
- [CI Pipeline](https://github.com/danimoya/AIVim-Editor/actions/workflows/ci.yml)
- [Test Suite](https://github.com/danimoya/AIVim-Editor/actions/workflows/test.yml)
- [Security Scan](https://github.com/danimoya/AIVim-Editor/actions/workflows/security.yml)
- [PyPI Publishing](https://github.com/danimoya/AIVim-Editor/actions/workflows/publish-to-pypi.yml)
- [Release Automation](https://github.com/danimoya/AIVim-Editor/actions/workflows/release-automation.yml)

## Contact

For release-related issues:
- Create an issue with `release` label
- Email: daniel.moya@dimensigon.com

## References

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Python Packaging Guide](https://packaging.python.org/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)