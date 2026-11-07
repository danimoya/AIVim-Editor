# 1.0 Alpha 1 — 2026-11-07

Minimal terminal workspace, floating AI controls, source context, live blocks with
review/automatic replacement, HTTPS/OpenShift setup, LAN/Tailscale model routing,
and a modern browser companion. Fixed sequential live-block offsets after newline
normalization. Added a real Bash demo GIF, workspace carousel and refreshed docs.
Python version `1.0.0a1`; Git tag `v1.0.0-alpha.1`.

# 0.6.0 — 2026-11-03

Document-safe saves and dirty-tab guards; lossless Unicode and bracketed paste; undo transactions; cancellable snapshot AI jobs and strict reviewed proposals; explicit NLP context; packaged browser security and ergonomics; unified settings, locks and qualification gates. Live provider entitlement and native-model qualification remain operator responsibilities; native Windows console and macOS terminal behavior require manual qualification.

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

## 1.0.0 — 2026-11-07

- Private atomic workspace recovery for unsaved buffers, cursor positions, sources and preferences; history persistence is opt-in. Live submission never resumes automatically.
- Find/replace, Vim search, go-to-line, file picker, indentation controls and editable proposals.
- Individual block retry/cancel, inline streaming ink with reduced-motion toggle, source freshness and explicit refresh.
- Named model profiles, live connection diagnostics and selection-based context limits for large documents.
- Non-executing Bash/Python/JSON syntax checks and reproducible live-model capture.

## 2.0.0 — 2026-11-07

- Explicit project folder, bounded local file/symbol/text context search, selectable source chunks and freshness.
- Reviewed multi-file AI changes, per-hunk acceptance, preflight conflict checks, private checkpoints, compensating rollback and interrupted-write recovery.
- Persistent generated-block instructions, mapped anchors, manual-edit detection and reviewed refinement/regeneration.
- Opt-in stdio language servers: UTF-16 text sync, diagnostics, plain-text completion, definition navigation and reviewed multi-file text rename.
- Explicit command/test execution with confirmation, deadlines, bounded output, cancellation and output-as-context for proposed fixes.
- Actual Olares1 multi-file recording and a separately evaluated clean Neovim RPC/grid/motion/undo prototype.

## 2.1.0 — 2026-11-07

- Wider five-line project prompt with scrolling, open/recent `@` file completion and Ctrl+Enter submission.
- Clickable filename tabs and a top-bar Edit → Live review → Live auto-replace control.
- Per-request language inference from explicit intent, shebang/extension, content and open project files.
- Animated AI activity; full-screen response view with Esc/Restore, prior pin-state restoration and reading-position preservation.
- Private user settings for editing defaults, spinner/pulse/Matrix activity, AIVIM Matrix startup, typing/instant/Matrix live ink, reduced motion and history persistence.
- Startup input routing preserves the first keystrokes; decorative previews remain separate from document edits.

## 2.1.1 — 2026-11-07

- Fixed floating AI Workbench dropdowns being covered by the instruction area and buttons. Every AI action is visible and clickable without pinning the panel.
- Verified every AI action through the workspace menu at compact terminal sizes, preserving the editor selection.
