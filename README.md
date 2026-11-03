# AIVim

AIVim is a local terminal editor with a browser companion and explicit AI review. Version 0.6.0 adds document safety, lossless Unicode input, undo/redo, bounded provider requests and validated proposals.

Install with Python 3.9 or newer:

```sh
python -m pip install aivim==0.6.0
aivim document.py
aivim-web --port 5000
```

The standard install includes OpenAI and Anthropic SDK adapters and the packaged browser assets. It does not compile a native inference engine or include model weights. `pyproject.toml` is dependency authority. `uv.lock` resolves the full optional dependency graph; `requirements-lock.txt` captures the qualified Python 3.9 Linux runtime with hashes.

Terminal editing supports `i`, `a`, `A`, `I`, `o`, `O`, `s`, arrows, `h/j/k/l`, `w/b/e`, `0/^/$`, `gg/G`, counted `dd` and `yy`, `p/P`, visual selections, `u` and Ctrl-R. An insert session is one undo transaction. `:w`, `:w filename`, `:saveas filename`, `:e`, `:e!`, `:q` and `:q!` manage documents. `:w!` explicitly overwrites an externally changed target. Save failures leave document identity, content and dirty state intact. UTF-8/BOM, loaded newline convention, final newline, target permissions and symlinks are preserved. Mixed newline input is normalized to the detected convention on save. Backups use unique names when enabled. Dirty tabs offer `:tabclose save`, `:tabclose discard`, or continuing editing to cancel. Exit checks every tab. `:n` / `:nexttab` and `:N` / `:prevtab` navigate tabs.

Substitution uses one parser: `:%s/pattern/replacement/g`, `:2,5s#pattern#replacement#gc`, or visual `:'<,'>s/.../.../`. Patterns are Python regular expressions; `g`, `c`, `i` and `I` flags are accepted. Escape a delimiter with a backslash. Confirmation accepts `y/n/a/q` without blocking further terminal reads.

AI commands are `:explain 1 10`, `:improve 1 10`, `:analyze 1 10`, `:generate 3 description`, and `:ai question`. Generation inserts before the specified one-based line, or at the end using line count + 1. Improvement, generation and NLP return proposals, never automatic edits. `:apply` changes the originating document as one undoable operation; `:y` creates a copy of the full proposed document; `:reject` dismisses it. Editing, closing or cancelling the originating document invalidates outstanding output. Escape cancels a request without dropping newer input or results. Explanations, analyses and chat responses stay outside the document.

NLP uses explicit `#nlp instruction`, paired `#nlp` markers, or `NLP-BEGIN` / `NLP-END` comment markers. Enter inserts a newline; F9 or `:nlptranslate` submits. Plain comments are not silently submitted. Live submission is opt-in and still requires proposal review. Cross-file context defaults to none. `:nlpcontext 2,3` selects tab numbers, `:nlpcontext` previews transmitted context, and `:nlpcontext none` clears it. A whole-source snapshot supplies stable character coordinates; each returned edit must lie inside marked ranges.

Configuration precedence is explicit CLI provider, explicit `--config`, `~/.config/aivim/settings.json`, then defaults. Ordinary settings use `schema_version: 1`. Explicit legacy INI files are accepted; API keys stay transient. Explicit injected credentials override environment credentials, which override legacy INI keys. Environment keys are `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. No `.env` files are automatically read. `aivim-config-migrate legacy.ini new-settings.json` preserves the original, refuses an existing destination and excludes credentials. Unsupported streaming, response caching, swap files and persistent undo are rejected clearly. The temperature setting applies to OpenAI and local inference; current Anthropic models use their provider default.

Configured defaults are `gpt-4.1-mini` and `claude-sonnet-5-5`, with model IDs overridable in settings. They are configured allowlists rather than entitlement claims. Real account authorization, model entitlement and budget must be qualified for your account before use. See [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [Anthropic models](https://platform.claude.com/docs/en/models/overview) and [Anthropic request parameters](https://platform.claude.com/docs/en/api/messages/create).

Default logs contain metadata, not code, prompts, keys or complete file paths. `:debug` explicitly enables content recording; files have mode 0600, directories 0700 and a configured retention count. Existing user documents and legacy configuration are never rewritten by migration or inference.

The browser companion binds to loopback and checks caller address, Host, Origin and CSRF. It renders AI text without HTML interpretation, preserves inputs on errors/cancellation, requires review before applying proposals, and offers copy/download and undo. Generation works with an empty document. Public hosting requires an explicit `create_app(mode='authenticated', principals=..., allowed_hosts=..., quota_path=..., secret_key=...)` operator configuration; bearer principals authorize providers and a SQLite transaction enforces shared quotas. This candidate makes the product decision explicit: the shipped CLI starts a single-user local companion. An operator may configure the authenticated factory for private hosting; no public service has been deployed.

Optional native inference is installed with `pip install '.[local-llm]'`. Configure a GGUF path and expected SHA-256, memory/CPU/thread/context limits, and explicitly select `local`. The model runs in a separate process that is terminated on cancellation/deadline. `aivim-model-download HTTPS_URL DESTINATION --sha256 DIGEST --max-bytes LIMIT` resumes a identified partial download, verifies size/header/checksum, and atomically installs it. No default model license, weights, machine or hardware quality is assumed. Native engine/model qualification remains an external release prerequisite.

Run qualification with `python -m pytest verification`, the retained `python -m unittest tests.test_buffer tests.test_history tests.test_utils`, and `python scripts/bump_version.py --validate`. Browser tests need Playwright Chromium; terminal tests use a real POSIX PTY. Historical tests using mocked editor dispatch are retained for comparison and are not presented as release evidence. [Release and rollback](docs/RELEASE.md) describes artifacts, platform qualification and operator steps. The bundled LICENSE is GPL v3; package metadata follows that file.

Optional local-model inference is unavailable on macOS because the required hard worker memory limit cannot be enforced. It fails before starting a worker; terminal/browser editing and remote provider adapters remain available. Linux and Windows workers require successfully established OS resource limits.
