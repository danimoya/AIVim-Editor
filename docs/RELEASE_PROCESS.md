# AIVim Release Process

This document describes the automated release process for AIVim.

## Overview

AIVim uses a fully automated release process that includes:

- 🔢 Automated version bumping
- 📝 Automatic changelog generation
- 🔐 Security scanning and attestations
- 📦 PyPI publishing with trusted publishing
- 📋 SBOM (Software Bill of Materials) generation
- ✅ Post-release validation

## Release Types

We follow [Semantic Versioning](https://semver.org/):

- **Patch** (0.5.X): Bug fixes, minor improvements
- **Minor** (0.X.0): New features, backwards-compatible
- **Major** (X.0.0): Breaking changes

## Creating a Release

### Automated Release (Recommended)

1. **Trigger the Release Workflow**

   Go to Actions → "Automated Release Management" → Run workflow

   Select the version bump type:
   - `patch`: Bug fixes (0.5.1 → 0.5.2)
   - `minor`: New features (0.5.1 → 0.6.0)
   - `major`: Breaking changes (0.5.1 → 1.0.0)

2. **What Happens Automatically**

   The workflow will:
   - ✅ Bump version in `pyproject.toml` and `VERSION` file
   - ✅ Generate changelog from commit messages
   - ✅ Update `CHANGELOG.md`
   - ✅ Create a git commit and tag
   - ✅ Create a GitHub release with release notes
   - ✅ Trigger the PyPI publishing workflow

3. **PyPI Publishing Workflow**

   Once the release is created, the publish workflow automatically:
   - ✅ Runs security scans (bandit, safety)
   - ✅ Runs critical tests
   - ✅ Validates version consistency
   - ✅ Builds the distribution packages
   - ✅ Generates SBOM and checksums
   - ✅ Creates build provenance attestations
   - ✅ Publishes to PyPI with attestations
   - ✅ Validates the published package
   - ✅ Uploads assets to GitHub release

### Manual Release (Advanced)

If you need manual control:

1. **Update Version**
   ```bash
   # Edit pyproject.toml
   version = "0.6.0"

   # Edit VERSION file
   echo "0.6.0" > VERSION
   ```

2. **Update Changelog**
   ```bash
   # Add entry to CHANGELOG.md
   ## [0.6.0] - 2025-10-12
   ### Added
   - New feature X
   - Enhancement Y
   ```

3. **Commit and Tag**
   ```bash
   git add pyproject.toml VERSION CHANGELOG.md
   git commit -m "chore: bump version to 0.6.0"
   git tag -a "v0.6.0" -m "Release v0.6.0"
   git push origin main --tags
   ```

4. **Create GitHub Release**

   Go to GitHub → Releases → Draft a new release
   - Select the tag you just created
   - Add release notes from CHANGELOG.md
   - Publish the release

## Commit Message Convention

For best changelog generation, use conventional commits:

```
feat: add new AI model support
fix: resolve buffer overflow in editor
docs: update installation guide
chore: update dependencies
ci: improve build performance
test: add tests for NLP mode
refactor: simplify command handler
perf: optimize syntax highlighting
```

### Commit Prefixes

- `feat:` - New features (→ "✨ New Features" section)
- `fix:` - Bug fixes (→ "🐛 Bug Fixes" section)
- `docs:` - Documentation (→ "📚 Documentation" section)
- `chore:`, `ci:`, `build:`, `deps:` - Maintenance (→ "🔧 Maintenance" section)
- `BREAKING CHANGE:` - Breaking changes (→ "⚠️ Breaking Changes" section)

## Pre-release Checklist

Before creating a release, ensure:

- [ ] All tests pass locally
- [ ] Code is reviewed and merged to `main`
- [ ] Documentation is updated
- [ ] No known critical bugs
- [ ] Security scans pass
- [ ] CHANGELOG.md is ready (or will be auto-generated)

## Release Workflow Details

### Security Checks

Before publishing, the workflow runs:

1. **Bandit Security Scanner**
   - Scans Python code for security issues
   - Checks for common vulnerabilities

2. **Safety Dependency Checker**
   - Checks dependencies for known vulnerabilities
   - Validates against CVE database

3. **Tests**
   - Runs critical test suite
   - Currently non-blocking (92 known failing tests)

4. **Manifest Check**
   - Validates package manifest
   - Ensures all files are included

5. **Version Consistency**
   - Validates version across files
   - Prevents version mismatches

### Build Process

1. **Package Building**
   ```bash
   python -m build
   ```
   Creates both wheel (.whl) and source distribution (.tar.gz)

2. **SBOM Generation**
   ```bash
   cyclonedx-py requirements --format json --output sbom.json
   ```
   Creates a Software Bill of Materials for supply chain security

3. **Checksum Generation**
   ```bash
   sha256sum dist/* > dist/SHA256SUMS
   sha512sum dist/* > dist/SHA512SUMS
   ```

4. **Build Attestation**
   - Creates cryptographic attestation of build provenance
   - Links artifacts to source code and build process
   - Published to PyPI for verification

### Publishing

1. **PyPI Upload**
   - Uses trusted publishing (no API keys in secrets)
   - OpenID Connect (OIDC) authentication
   - Automatic attestation publishing

2. **Post-Publish Validation**
   - Waits for package to be available
   - Installs from PyPI
   - Verifies import and CLI work

3. **GitHub Release**
   - Uploads distribution files
   - Uploads SBOM
   - Uploads checksums

## Verifying a Release

### Verify Package Integrity

```bash
# Download from GitHub release
wget https://github.com/danimoya/AIVim-Editor/releases/download/v0.5.1/aivim-0.5.1.tar.gz
wget https://github.com/danimoya/AIVim-Editor/releases/download/v0.5.1/SHA256SUMS

# Verify checksum
sha256sum -c SHA256SUMS
```

### Verify PyPI Attestations

```bash
# Install with attestation verification (Python 3.11+)
pip install --verify-attestations aivim
```

### Check SBOM

Download `sbom.json` from the GitHub release to see all dependencies.

## Troubleshooting

### Release Fails at Publishing

- Check PyPI credentials are configured
- Verify version doesn't already exist on PyPI
- Check if package name is available

### Tests Fail

- Review test output in workflow logs
- Fix failing tests before release
- Currently tests are non-blocking but should be fixed

### Attestation Fails

- Ensure repository has OIDC enabled
- Verify permissions are correct
- Check GitHub Actions token has needed permissions

### Version Mismatch

- Ensure VERSION file matches pyproject.toml
- Run version validation locally:
  ```bash
  python -c "
  import re
  from pathlib import Path
  pyproject = Path('pyproject.toml').read_text()
  version = re.search(r'version = \"(.+?)\"', pyproject).group(1)
  version_file = Path('VERSION').read_text().strip()
  assert version == version_file, f'Mismatch: {version} != {version_file}'
  print(f'Version OK: {version}')
  "
  ```

## Emergency Hotfix

For critical security fixes:

1. Create hotfix branch from the release tag
2. Apply minimal fix
3. Create patch release immediately
4. Follow same release process
5. Notify users through GitHub security advisory

## Rollback

If a release has critical issues:

1. **Yank from PyPI** (doesn't delete, marks as unusable)
   ```bash
   twine yank aivim 0.5.1
   ```

2. **Mark GitHub Release as pre-release**
   - Edit the release
   - Check "This is a pre-release"

3. **Create fixed release immediately**
   - Follow hotfix process above

## Post-Release Tasks

After a successful release:

- [ ] Announce on relevant channels
- [ ] Update documentation website
- [ ] Monitor for issues in first 48 hours
- [ ] Review automated dependency updates
- [ ] Plan next release features

## Resources

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [SLSA Build Provenance](https://slsa.dev/spec/v1.0/provenance)
