# AIVim workspace

Run `aivim-web --port 5000`, then open <http://127.0.0.1:5000>.
The Python package contains the built frontend; Node is needed only to change it.
Provider credentials follow the existing environment/configuration rules. A provider
must be configured to generate; editing, sources, copy and download work without one.

## First workflow

1. Open a UTF-8 text file. Files open in separate document tabs.
2. In **Sources**, add reference text files, code, Markdown, notes, or a snapshot of
   the current document. Check the sources for the next request. Uncheck anything
   that should not be transmitted.
3. Return to **Editor** and select text with the mouse or Vim Visual mode.
4. Choose **Rewrite**, **Explain**, **Analyze**, or **Ask AI**. Enter instructions
   in the AI panel when needed. `Ctrl/Cmd+Enter` submits from the editor or prompt.
5. Read the streamed preview and the final unified diff. Accept or reject the
   change. **Undo** or `Ctrl/Cmd+Z` restores the selection; Vim `u` also works.

**New with AI** creates an empty document and selects generation. Generation inserts
at the cursor. Choose the output language and optional sources, describe the output,
and submit. Rewrite/explain/analyze require a selection. Questions can use a selection
or just the checked sources and optional nearby text.

**Vim keys** toggles Normal/Insert/Visual behavior. Mouse selection and toolbar
buttons work in both input modes. `:w` downloads the current buffer. Browser Vim
bindings do not provide the complete Vim plugin/runtime ecosystem.

The context preview shows checked source snapshots and, when enabled, up to 2,000
characters before and after the target. Only the target and that context are sent
to the provider. The complete document snapshot is sent to the local backend for
proposal validation, not forwarded to the provider. Each request captures its source
selection; changing the Sources tab while it runs affects later requests.

## Live natural language blocks

Live mode is off by default. Enable **Live natural language → code** on a blank
line and write an instruction. A single Enter continues the same instruction.
Enter twice creates an empty line and submits the completed block. A line containing
only spaces/tabs also counts as blank. Continue typing the next instruction below it.
This mode treats typed blocks as instructions; turn it off when editing ordinary code.
Pasting or dropping text alone does not submit it; type the closing blank line to submit.

For example, type:

```text
Create a Python function that adds two numbers.
Include type hints and a short docstring.

Create an example calling that function.

```

The two instructions are queued separately, in order (up to ten waiting blocks).
Remote provider tokens stream into the AI panel. Completed output is parsed and
validated before replacement. By default it waits for **Accept change**; the next
queued block waits until you accept or reject the current one.

Enable **Replace completed blocks automatically** to replace each instruction with
its completed code without another click. This is an explicit opt-in. Partial output
stays in the preview, so typing and cursor movement are not interrupted by token
insertions. Replacement is one undoable transaction; undo restores the original
instruction. Local GGUF inference currently returns a completed preview without token
streaming.

Editing a submitted instruction invalidates its result. Edits before it move its
anchors; edits outside it, including typing the next block, are preserved. Undo/redo
does not resubmit instructions. Cancel clears the waiting queue and cancels the active
request. Turning live mode off also cancels queued/active live work. Failed or truncated
responses leave the instruction intact and never become applicable proposals.

## Session data and limits

Documents, checked sources, and history live in browser memory. Reloading or closing
loses them; download documents you want to retain. History retains the latest 50
requests with their context snapshots, results and acceptance state. Open files are
not written back to disk automatically. Text files must be valid UTF-8 and contain no
NUL bytes. Local editing accepts files up to 20 MiB; AI requests currently accept a
50 KiB document snapshot and 50 KiB of context, with an 8 KiB instruction limit.
Each source is limited to 50 KiB, with at most 30 sources. Large aggregate context is
rejected visibly, not silently truncated. URL/PDF ingestion, persistent workspaces,
per-hunk acceptance, and rendered Markdown previews are outside this first version.

## Development and verification

```sh
npm ci
npm run build
npm test
python -m pip install -e '.[test]'
python -m playwright install chromium
python -m pytest verification
python -m unittest tests.test_buffer tests.test_history tests.test_utils
python scripts/bump_version.py --validate
```

Edit `frontend/app.js` and `frontend/blocks.js`; `aivim/web/static/app.js` is generated.
The build also writes notices for the libraries actually bundled. Check in the bundle
and notices so a Python-only install works offline without third-party asset CDNs.

`POST /api/ai-stream` uses the same validation, CSRF, provider authorization and quotas
as `/api/ai-assist`. The response is newline-delimited JSON: `start`, zero or more
`delta` events, and `done` or `error`. Only `done` carries a validated proposal.
Selections use zero-based Python character offsets in the immutable document snapshot;
the browser converts UTF-16 positions before transmission. After sending, the browser
maps target anchors through edits and applies only if the original target still matches.
Both remote SDK transports enforce deadlines, cancellation, output limits and completion
status; partial streams are never retried or applied. The optional local adapter uses
its existing bounded worker and emits a single completed delta.

Browser verification uses local HTTP stubs through the real SDK adapters. It covers
selected-source exclusion, Unicode offsets, Vim editing, review/undo, provider failures,
stream cancellation, live block queuing, stale results, mobile overflow and large files.
It does not establish live-account provider entitlement or generated-code quality.
