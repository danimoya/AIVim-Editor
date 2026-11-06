# AIVim 1.0 Alpha 1

**Python package:** `1.0.0a1` · **Git tag:** `v1.0.0-alpha.1`

A terminal-first revamp with two permanent UI rows, floating menus and AI controls,
optional sidebar pinning, Vim-style/standard input, mouse selection, right-click
selection actions and tooltips.

The alpha adds live natural-language instruction blocks with streamed previews,
review or opt-in automatic replacement, source snapshots and session history.
Each accepted change is one undoable edit. Exact edit spans and normalized newline
lengths keep sequential requests anchored correctly; edited targets become stale.

Model connections include an HTTPS/OpenShift setup dialog, masked bearer-token
entry, optional private credential storage, model discovery and private-CA support.
Local model servers support LAN-first/Tailscale fallback before connection;
partial responses are never replayed. Existing OpenAI, Anthropic, local GGUF and
classic curses interfaces remain available. The optional browser workspace gains
CodeMirror/Vim editing, sources, review and streaming.

The README includes a real Bash live-replacement recording, a looping workspace
carousel and screenshot links. Idle inference pauses are shortened; generated
commands are syntax-checked but never executed. The recorder and sanitized demo
provenance are included for reproduction.

This is an alpha: Vim runtime/plugin compatibility, persistent sessions/history,
LSP features, PDF/URL ingestion and per-hunk acceptance are not implemented.

## Upgrade and rollback

Install the tagged source or an attached wheel in an isolated environment. Existing
JSON settings remain valid. User-specific endpoint URLs, credentials and firewall
rules are outside this repository. Select the previous environment/version to roll
back while retaining documents and the original settings file. Do not overwrite
user configuration during upgrade.

## Publication

This is a GitHub prerelease. Prerelease publication verifies/builds distribution
artifacts but does not automatically publish to PyPI. An explicit package-publish
workflow dispatch is a separate operation. See `docs/RELEASE.md` for qualification.
