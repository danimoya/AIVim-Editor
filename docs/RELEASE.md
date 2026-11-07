# Release qualification and rollback

The 1.0 alpha release is **1.0 Alpha 1**, with Python version `1.0.0a1`, frontend
version `1.0.0-alpha.1`, and Git tag `v1.0.0-alpha.1`. See the
[alpha release notes](RELEASE_NOTES_1.0_ALPHA.md) for scope and limitations.

## Version identity

`aivim/_version.py` is the Python authority. `VERSION`, `package.json` and the root
of `package-lock.json` mirror it using the appropriate Python/SemVer spelling.

```sh
python scripts/bump_version.py 1.0.0a1
uv lock
python scripts/bump_version.py --validate
python scripts/bump_version.py --tag
```

The bump tool supports alpha, beta and release-candidate versions. Release tags
are checked through the same mapping; Python package filenames use PEP 440 spelling.
Never hand-edit only a single version mirror.

## Qualification

1. Install `.[test,build,terminal-syntax]` in an isolated environment and install
   Playwright Chromium. Run all `verification` tests, retained Buffer/History/Utils
   unittests, static source parsing and version validation.
2. Rebuild the browser bundle with `npm ci && npm test && npm run build`. Check
   that committed JS and bundled license notices reproduce exactly.
3. Build wheel and sdist in a disposable directory; run `python -m twine check`.
   Install the wheel into a fresh environment and run `scripts/installed_smoke.py`
   from outside the checkout. Rebuild the sdist independently. Record SHA-256 sums.
4. `qualification.yml` is the automatic supported contract suite: frontend checks,
   Linux/macOS/Windows and Python 3.9/3.11/3.13. The old `ci.yml` and `test.yml`
   contain historical tests and are retained as manual-only comparison workflows.
   Local Linux results do not establish native macOS/Windows console behavior.
5. Loopback fixtures test real SDK/HTTP/HTTPS behavior with synthetic credentials.
   Live provider checks require configured credentials and model entitlement; local
   model availability, native inference resource limits and generation quality
   remain hardware/operator-specific. No model weights or production keys ship.
6. Demo recordings use real application events and the configured model. Generated
   Bash is syntax-checked without execution. Publish only the GIF, poster and
   sanitized provenance; raw temporary frames and machine settings stay local.

## Publication

Push the reviewed commit and matching tag, then create a GitHub prerelease.
The manual **Prepare GitHub release** workflow uses the already-committed version;
it does not edit metadata or push version bumps behind the reviewer's back.

A published GitHub release triggers verification and artifact creation.
**Prereleases skip automatic PyPI publication** and can attach verified distribution
assets to GitHub. Stable releases retain the explicit PyPI publication path.
An intentional `workflow_dispatch` can target TestPyPI or PyPI separately.
GitHub publication never deploys a web service or rewrites user configuration.

User-specific endpoint URLs, bearer tokens, CA files, host firewall rules and model
configuration are outside this repository. Inspect staged files before pushing.
Release notes should distinguish loopback qualification from live inference evidence.

## Rollback

Keep the previously qualified artifact and lock. Install it in a separate environment
and retain original JSON/INI configuration, documents and backups. Configuration
migration refuses destination overwrite and excludes credentials. The new UI can be
bypassed with `aivim --classic`; that is an interface choice, not a downgrade of
shared services. Avoid rewriting user files during rollback.

Local GGUF inference remains unavailable on macOS when the required hard worker
memory limit cannot be enforced. Linux/Windows workers must establish their OS
resource limits. Terminal editing and remote model providers remain available.

## Stable 1.0 gate and order

Recovery and private snapshots → search/editing essentials → individual live-block
controls and inline ink → actual selection/context budgets → model profiles and
diagnostics → real local-model capture → package and cross-platform qualification.

The 1.0 gate includes forced-process-exit recovery, 100 sequential SDK-streamed
replacements with undo/redo, disconnected-provider preservation, stale selection
protection, real terminal dispatch, and installed-wheel checks. Desktop terminal,
SSH and tmux behavior should also be checked manually where available.

## 2.0 delivery sequence

1. Explicit project folder and file/symbol context search with a send preview.
2. Reviewed multi-file change sets, per-file/per-hunk acceptance, checkpoints and rollback.
3. Persistent instruction blocks with regeneration and manual-edit conflict detection.
4. Opt-in language-server diagnostics, completion, definitions and rename.
5. Explicit command/test execution, captured output as context, and reviewed fixes.
6. Evaluate Neovim RPC embedding separately before promising full Vim compatibility.
