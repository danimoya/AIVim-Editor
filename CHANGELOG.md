# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.4] - 2025-10-12

### 🐛 Fixed

- Fixed checksum files causing PyPI upload errors
- Moved SHA256SUMS and SHA512SUMS out of dist/ folder
- Separated checksum artifact upload from distribution packages
- Added checksums to GitHub release assets

### 🔧 Improved

- Checksums now properly included in GitHub releases
- Better artifact organization for releases
- Cleaner PyPI upload process

## [0.5.3] - 2025-10-12

### 🐛 Fixed

- Fixed PyPI publishing workflow to work with private repositories
- Disabled attestations for private repos (can be enabled when public)
- Corrected permissions in publish workflow

### 📝 Changed

- Updated documentation to reflect private repository compatibility
- Added clear instructions for enabling attestations on public repositories

## [0.5.2] - 2025-10-12

### ✨ Added

- Automated release workflow with semantic versioning
- SBOM (Software Bill of Materials) generation for supply chain security
- Build provenance attestations using SLSA standards
- SHA256/SHA512 checksum generation for all release artifacts
- Repository health monitoring workflow (daily checks)
- Automated dependency update workflow (weekly updates)
- Comprehensive pull request template

### 🔐 Security

- Enhanced PyPI publishing with attestations
- Attestation publishing to PyPI for package verification
- Pinned dependencies with cryptographic hashes
- Automated security vulnerability scanning

### 📚 Documentation

- Complete release process documentation
- Improvements summary document
- PR template with security and quality checklists

### 🔧 Improvements

- Reduced release time from hours to minutes
- Better supply chain security with verifiable releases
- Continuous health monitoring and quality checks
- Automated dependency management

## [0.5.1] - Previous Release

See GitHub releases for earlier versions.

[0.5.4]: https://github.com/danimoya/AIVim-Editor/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/danimoya/AIVim-Editor/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/danimoya/AIVim-Editor/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/danimoya/AIVim-Editor/releases/tag/v0.5.1
