# AIVim 2.1 project workflows

Run `aivim --project ./project` or use **Open project** in Ctrl+P. Relative filename
arguments are interpreted inside the selected project. Project tools also appear
in the floating ≡ menu. No project configuration executes automatically. Recovery chooses snapshots for the
explicit project root, so opening another project does not restore unrelated buffers.

## Choose context

**Search project** finds file names, symbol text and ordinary text. Search is local;
choose exact result chunks to add to Sources and inspect them before a request.
Git projects honor tracked/untracked file exclusions. Generated directories, `.env`
files and private key/certificate files are excluded from project search and writes.
Search visits at most 2,000 files of 256 KiB each, scanning at most 10 MiB per query.
No semantic index or background upload is created.

File context retains its path and digest. Source freshness checks the underlying
file; refreshing a chunk reloads its recorded line range. Already-submitted requests
retain their immutable snapshots. Normal selection requests send only checked
chunks. Multi-file generation uses complete checked project files (50 KiB total),
so it can propose complete replacement files with coherent diffs.

## Review a change set

Choose **Generate project change**. The wider prompt shows five text lines and
scrolls vertically for longer instructions. Enter inserts a line; Ctrl+Enter or the
Generate button submits. Type `@` to complete open or recent files with arrows,
Tab/Enter or a mouse click. Filenames with spaces are quoted automatically.

Mentioned saved files inside the project are included as editable snapshots.
Unsaved buffers and files outside the project are read-only references; save an
unsaved target before requesting edits to that existing file. Unmentioned open or
recent files are not sent. Missing or oversized references fail visibly. Recent
paths and interface preferences stay in private local state.

Describe the task and wait for a proposal.
Existing files must have been included in checked context; new files must stay
inside the project. Up to 20 files and 1 MiB of output are supported. No files are
changed by receiving a proposal.

The review overlay lists selectable hunks for every file and shows unified diffs.
Uncheck a file's hunks to keep that file unchanged. **Apply checked hunks** explicitly
writes the selected changes. Save or discard unsaved target buffers first. External
changes invalidate the proposal. File formats, permissions and conflict checks use
the same transactional FileStore as ordinary saving.

A private journal is written before the first file write. Applying multiple files
uses preflight checks and compensating rollback, not a filesystem-wide atomic commit.
**Roll back checkpoint** restores the last operation if no affected file has newer
edits. **Project checkpoints** also lists interrupted operations after a crash,
including a write interrupted before its journal confirmation. Conflicting newer
edits are preserved and reported. New files created by a rolled-back change are
removed. Checkpoints are private local recovery data, not Git commits.

## Keep the instruction behind the code

Accepted generated blocks retain their original instruction, generated content,
model and mapped range. Metadata is stored in private workspace snapshots, never
inserted into source files. **Instruction blocks** lets you refine/regenerate one.
Manual edits mark it as edited; the current block is included in regeneration
context and the result always requires review. Edits outside a block move its
anchors. Undo/redo and recovery retain provenance; they never submit AI requests.

## Language intelligence

Install a language server separately. For Python:

```sh
pipx install 'python-lsp-server[pyflakes]'
```

Or include the optional dependency group when installing AIVim:

```sh
pip install 'aivim[terminal-syntax,python-lsp]==2.1.0'
```

Open a project and a saved file. Choose **Start language server**, then enter `pylsp`.
This explicitly starts a local process; server startup is never restored automatically.
The stdio LSP client supports UTF-16 positions and full text synchronization.
Ctrl+P exposes diagnostics, plain-text completion, definition navigation and rename.
Snippets and arbitrary server commands/resource operations are not applied. Save
buffers before multi-file rename; returned text edits use the same hunk review and
checkpoint flow as AI changes. Large rename snapshots are bounded at 32 MiB.

## Tests and commands

**Run command / tests** accepts an executable and arguments. A confirmation shows
the exact command and project directory. Shell expansion, pipes and redirects are
not implicit; explicitly invoking a shell is an ordinary user-selected command.
Runs have a 60-second deadline, a 256 KiB output budget and a **Stop command** action.
Closing the workspace cancels the active command. Use **Use command output** to add
output as a checked source, or **Fix from test output** to request a reviewed change.
A model response never starts a process. Generated code is not executed on acceptance.

## Neovim evaluation

`pip install 'aivim[neovim-probe]'` installs the optional RPC client. With Neovim
installed, run `python scripts/probe_neovim.py`. It starts a clean child without
user plugins, attaches the external grid, exercises real Vim motion and undo, and
reports timing. The tested prototype supports an embedded-engine experiment; 2.0
continues to use Textual while that integration is evaluated separately.
