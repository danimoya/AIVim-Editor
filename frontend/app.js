import { EditorState, Compartment, Annotation } from "@codemirror/state";
import {
  EditorView,
  keymap,
  lineNumbers,
  highlightActiveLine,
  drawSelection,
} from "@codemirror/view";
import {
  history,
  historyKeymap,
  defaultKeymap,
  undo,
  redo,
  isolateHistory,
} from "@codemirror/commands";
import {
  syntaxHighlighting,
  defaultHighlightStyle,
  bracketMatching,
} from "@codemirror/language";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { markdown } from "@codemirror/lang-markdown";
import { vim, Vim, getCM } from "@replit/codemirror-vim";
import { completedBlock, partialCode, mapTarget } from "./blocks.js";

const el = (id) => document.getElementById(id),
  status = (text) => {
    el("status").textContent = text;
  };
const aiEdit = Annotation.define(),
  vimConfig = new Compartment(),
  languageConfig = new Compartment();
const docs = [],
  sources = [],
  records = [],
  pending = [];
let current,
  active = null,
  proposal = null,
  csrf = "",
  capabilities = {},
  ready = false;
const textOf = (doc) => doc.state.doc.toString();
const modeExtensions = () => (el("vim").checked ? [vim()] : []);
const languageExtensions = () =>
  ({
    python: python(),
    javascript: javascript(),
    markdown: markdown(),
    text: [],
  })[el("language").value];
const theme = EditorView.theme(
  {
    "&": { backgroundColor: "#11141b", color: "#e5eaf2" },
    ".cm-gutters": {
      backgroundColor: "#11141b",
      color: "#57657b",
      border: "none",
    },
    ".cm-activeLine": { backgroundColor: "#1a2230" },
    ".cm-cursor": { borderLeftColor: "#b5e4b0" },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection":
      { backgroundColor: "#334e4b" },
    ".cm-content": { caretColor: "#b5e4b0" },
  },
  { dark: true },
);
const view = new EditorView({ parent: el("editor"), state: makeState("") });
function makeState(text) {
  return EditorState.create({
    doc: text,
    extensions: [
      lineNumbers(),
      drawSelection(),
      highlightActiveLine(),
      history(),
      bracketMatching(),
      syntaxHighlighting(defaultHighlightStyle),
      theme,
      EditorView.cspNonce.of(
        document.querySelector("meta[name=csp-nonce]").content,
      ),
      vimConfig.of(modeExtensions()),
      languageConfig.of(languageExtensions()),
      keymap.of([
        {
          key: "Mod-Enter",
          run: () => {
            submit();
            return true;
          },
        },
        ...defaultKeymap,
        ...historyKeymap,
      ]),
      EditorView.contentAttributes.of({
        "aria-label": "Document",
        spellcheck: "false",
      }),
      EditorView.updateListener.of(changed),
    ],
  });
}
function changed(update) {
  if (!current) return;
  current.state = update.state;
  if (update.docChanged) {
    current.dirty = true;
    for (const target of [active, proposal, ...pending].filter(Boolean)) {
      if (target.docId !== current.id || target.invalid) continue;
      Object.assign(target, mapTarget(target, update.changes));
    }
    if (proposal?.invalid) {
      proposal.record.state = "Stale";
      clearProposal();
      renderHistory();
      status(
        "Stale proposal: selected text changed. Ask for a fresh proposal.",
      );
    }
    if (current.liveFrom !== null)
      current.liveFrom = update.changes.mapPos(current.liveFrom, -1);
    const typed = update.transactions.some(
      (tr) =>
        tr.isUserEvent("input") &&
        !tr.isUserEvent("input.paste") &&
        !tr.isUserEvent("input.drop"),
    );
    if (
      typed &&
      el("live").checked &&
      !update.transactions.some((tr) => tr.annotation(aiEdit)) &&
      !update.view.composing
    ) {
      const block = completedBlock(
        textOf(current),
        current.liveFrom,
        update.state.selection.main.head,
      );
      if (block) {
        current.liveFrom = block.next;
        if (pending.length >= 10) {
          status(
            "Live queue is full. Submit the remaining instruction manually.",
          );
        } else {
          pending.push({
            ...block,
            docId: current.id,
            base: textOf(current),
            original: textOf(current).slice(block.from, block.to),
            context: contextFor(current, block.from, block.to),
            instruction: block.instruction,
            auto: el("auto-apply").checked,
            live: true,
            invalid: false,
          });
          pump();
        }
      }
    }
  }
  updateSelection();
}
function newDocument(name = "untitled.py", content = "") {
  const doc = {
    id: crypto.randomUUID(),
    name,
    state: makeState(content),
    dirty: false,
    language: el("language").value,
    liveFrom: null,
  };
  docs.push(doc);
  switchDocument(doc);
  return doc;
}
function switchDocument(doc) {
  if (current) current.state = view.state;
  current = doc;
  view.setState(doc.state);
  el("language").value = doc.language;
  view.dispatch({
    effects: [
      vimConfig.reconfigure(modeExtensions()),
      languageConfig.reconfigure(languageExtensions()),
    ],
  });
  doc.liveFrom = el("live").checked ? view.state.selection.main.head : null;
  renderDocuments();
  updateSelection();
  renderContext();
}
function renderDocuments() {
  el("documents").replaceChildren(
    ...docs.map((doc) => {
      const b = document.createElement("button");
      b.textContent = doc.name;
      b.classList.toggle("active", doc === current);
      b.onclick = () => switchDocument(doc);
      return b;
    }),
  );
  el("document-name").textContent = current.name;
}
function updateSelection() {
  const { from, to, head } = view.state.selection.main,
    line = view.state.doc.lineAt(head);
  el("position").textContent = `Ln ${line.number}, Col ${head - line.from + 1}`;
  el("selection-label").textContent =
    from === to
      ? "Select text to work with AI"
      : `${to - from} characters selected`;
  document
    .querySelectorAll("[data-action]")
    .forEach((b) => (b.disabled = from === to && b.dataset.action !== "query"));
  const cm = getCM(view);
  el("mode").textContent = !el("vim").checked
    ? "STANDARD"
    : cm?.state.vim?.insertMode
      ? "INSERT"
      : cm?.state.vim?.visualMode
        ? "VISUAL"
        : "NORMAL";
  el("undo").disabled = !current;
  renderContext();
}
function tab(name) {
  document
    .querySelectorAll(".workspace-panel")
    .forEach((p) => (p.hidden = p.id !== name + "-tab"));
  document.querySelectorAll("[data-tab]").forEach((b) => {
    const selected = b.dataset.tab === name;
    b.classList.toggle("active", selected);
    b.setAttribute("aria-selected", selected);
  });
  if (name === "editor") view.requestMeasure();
}
document
  .querySelectorAll("[data-tab]")
  .forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
el("manage-sources").onclick = () => tab("sources");
el("new-document").onclick = () => {
  newDocument();
  view.focus();
};
el("new-ai").onclick = () => {
  newDocument();
  tab("editor");
  el("action").value = "generate";
  el("instruction").focus();
  status("Describe a new document and choose sources, then Ask AI.");
};
el("vim").onchange = () => {
  view.dispatch({ effects: vimConfig.reconfigure(modeExtensions()) });
  updateSelection();
  view.focus();
};
el("language").onchange = () => {
  current.language = el("language").value;
  view.dispatch({ effects: languageConfig.reconfigure(languageExtensions()) });
};
el("undo").onclick = () => {
  undo(view);
  view.focus();
};
el("redo").onclick = () => {
  redo(view);
  view.focus();
};
el("live").onchange = () => {
  current.liveFrom = el("live").checked
    ? view.state.doc.lineAt(view.state.selection.main.head).from
    : null;
  if (!el("live").checked) cancelLive();
  status(
    el("live").checked
      ? "Live mode armed at the current line. Enter twice submits a block."
      : "Live mode off.",
  );
  view.focus();
};
el("auto-apply").onchange = () =>
  status(
    el("auto-apply").checked
      ? "Live blocks will replace their instructions when complete. Undo restores each instruction."
      : "Live blocks will wait for review before replacement.",
  );
function cancelLive() {
  pending.length = 0;
  if (active?.live) cancelRequest();
}
function contextFor(doc, from, to) {
  const context = {
    sources: sources
      .filter((s) => s.selected)
      .map((s) => ({ id: s.id, name: s.name, content: s.content })),
  };
  if (el("surrounding").checked) {
    const text = textOf(doc);
    context.nearby = {
      before: text.slice(Math.max(0, from - 2000), from),
      after: text.slice(to, to + 2000),
    };
  }
  return JSON.stringify(context, null, 2);
}
function renderContext() {
  if (!current) return;
  const selected = sources.filter((s) => s.selected);
  el("source-count").textContent = String(selected.length);
  el("context-chips").replaceChildren();
  if (!selected.length) el("context-chips").textContent = "No sources selected";
  for (const source of selected) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = source.name;
    el("context-chips").append(chip);
  }
  const { from, to } = view.state.selection.main;
  el("context-preview").textContent = contextFor(current, from, to);
}
el("surrounding").onchange = renderContext;
function addSource(name, content) {
  if (new TextEncoder().encode(content).length > 50 * 1024)
    throw new Error("Each source must be at most 50 KiB.");
  if (sources.length >= 30)
    throw new Error("This workspace supports up to 30 sources.");
  sources.push({ id: crypto.randomUUID(), name, content, selected: true });
  renderSources();
}
function renderSources() {
  el("source-list").replaceChildren();
  if (!sources.length)
    el("source-list").textContent =
      "Add a reference file or paste your first note.";
  for (const source of sources) {
    const card = document.createElement("article");
    card.className = "source-card";
    const label = document.createElement("label"),
      check = document.createElement("input");
    check.type = "checkbox";
    check.checked = source.selected;
    check.onchange = () => {
      source.selected = check.checked;
      renderContext();
    };
    label.append(check, document.createTextNode(source.name));
    const pre = document.createElement("pre");
    pre.textContent = source.content;
    const remove = document.createElement("button");
    remove.textContent = "Remove";
    remove.onclick = () => {
      sources.splice(sources.indexOf(source), 1);
      renderSources();
    };
    card.append(label, pre, remove);
    el("source-list").append(card);
  }
  renderContext();
}
el("source-form").onsubmit = (e) => {
  e.preventDefault();
  try {
    addSource(el("source-name").value, el("source-content").value);
    e.target.reset();
  } catch (err) {
    status(err.message);
    alert(err.message);
  }
};
el("add-document-source").onclick = () => {
  try {
    addSource(current.name, textOf(current));
  } catch (err) {
    alert(err.message);
  }
};
async function readText(file, max) {
  if (file.size > max)
    throw new Error(`File exceeds the ${max / 1024} KiB limit.`);
  const text = new TextDecoder("utf-8", { fatal: true }).decode(
    await file.arrayBuffer(),
  );
  if (text.includes("\0")) throw new Error("Binary files cannot be opened.");
  return text;
}
el("source-upload").onchange = async () => {
  try {
    for (const file of el("source-upload").files)
      addSource(file.name, await readText(file, 50 * 1024));
  } catch (err) {
    alert(err.message);
  } finally {
    el("source-upload").value = "";
  }
};
el("upload").onchange = async () => {
  try {
    const file = el("upload").files[0];
    if (!file) return;
    newDocument(file.name, await readText(file, 20 * 1024 * 1024));
    status("Local file opened. No content sent to a provider.");
  } catch (err) {
    status(err.message);
  } finally {
    el("upload").value = "";
  }
};
function models() {
  el("model").replaceChildren(
    ...(capabilities[el("provider").value]?.models || []).map((m) => {
      const o = document.createElement("option");
      o.value = m;
      o.textContent = m;
      return o;
    }),
  );
}
el("provider").onchange = models;
async function jsonResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Server returned an unreadable response");
  }
  if (!response.ok) throw new Error(data.error?.message || "Request failed");
  return data;
}
fetch("/api/capabilities")
  .then(jsonResponse)
  .then((data) => {
    csrf = data.csrf_token;
    capabilities = data.providers;
    for (const [p, v] of Object.entries(capabilities)) {
      const o = document.createElement("option");
      o.value = p;
      o.textContent = p + (v.available ? "" : " — unavailable");
      el("provider").append(o);
    }
    if (data.selection) el("provider").value = data.selection.provider;
    models();
    ready = true;
    el("submit").disabled = false;
    status("Ready. Select text or describe something new.");
  })
  .catch((err) => status(err.message));
function clearProposal() {
  proposal = null;
  el("apply").disabled = true;
  el("reject").disabled = true;
}
function requestBusy(busy) {
  el("submit").disabled = busy || !ready;
  el("cancel").disabled = !busy;
}
function submit() {
  if (active || !ready) return;
  const { from, to } = view.state.selection.main,
    action = el("action").value;
  if (["improve", "explain", "analyze"].includes(action) && from === to) {
    status("Select the text you want AI to work on first.");
    return;
  }
  const start = action === "generate" ? view.state.selection.main.head : from,
    end = action === "generate" ? start : to;
  run({
    ...{ from: start, to: end },
    docId: current.id,
    base: textOf(current),
    original: textOf(current).slice(start, end),
    context: contextFor(current, start, end),
    instruction: el("instruction").value,
    action,
    live: false,
    invalid: false,
  });
}
document.querySelectorAll("[data-action]").forEach(
  (b) =>
    (b.onclick = () => {
      el("action").value = b.dataset.action;
      if (b.dataset.action === "query") el("instruction").focus();
      else submit();
    }),
);
el("submit").onclick = submit;
el("instruction").onkeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    submit();
  }
};
function pump() {
  if (active || proposal || !ready) return;
  while (pending.length) {
    const target = pending.shift();
    if (target.invalid) continue;
    target.action = "generate";
    run(target);
    break;
  }
}
async function run(target) {
  if (new TextEncoder().encode(target.context).length > 50 * 1024) {
    status(
      "Selected context exceeds 50 KiB. Uncheck sources or nearby document text.",
    );
    return;
  }
  if (proposal) proposal.record.state = "Superseded";
  clearProposal();
  const id = crypto.randomUUID(),
    controller = new AbortController();
  active = { ...target, id, controller };
  const request = active,
    doc = docs.find((d) => d.id === target.docId);
  if (!doc) {
    active = null;
    return;
  }
  // Queue coordinates track edits, while the immutable request uses the current document snapshot.
  request.base = textOf(doc);
  const initialFrom = request.from,
    initialTo = request.to;
  request.original = request.base.slice(initialFrom, initialTo);
  requestBusy(true);
  el("result").textContent = "";
  status(
    request.live
      ? "Generating completed instruction block…"
      : "Pending: contacting selected provider…",
  );
  const record = {
    id,
    document: doc.name,
    instruction: request.instruction,
    action: request.action,
    context: request.context,
    state: "Pending",
    result: "",
    time: new Date().toLocaleTimeString(),
  };
  records.unshift(record);
  if (records.length > 50) records.pop();
  request.record = record;
  renderHistory();
  const charOffset = (pos) => Array.from(request.base.slice(0, pos)).length;
  const payload = {
    request_id: id,
    action: request.action,
    provider: el("provider").value,
    model: el("model").value,
    language: doc.language,
    code: request.base,
    context: request.context,
    specification: request.action === "generate" ? request.instruction : "",
    query: request.action !== "generate" ? request.instruction : "",
    selection_start: charOffset(initialFrom),
    selection_end: charOffset(initialTo),
  };
  let raw = "",
    finished = false;
  try {
    const response = await fetch("/api/ai-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      signal: controller.signal,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      await jsonResponse(response);
      return;
    }
    const reader = response.body.getReader(),
      decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        if (!line.trim()) continue;
        const message = JSON.parse(line);
        if (active !== request) return;
        if (message.type === "delta") {
          raw += message.data;
          el("result").textContent = ["improve", "generate"].includes(
            request.action,
          )
            ? partialCode(raw)
            : raw;
        }
        if (message.type === "error") throw new Error(message.data.message);
        if (message.type === "done") {
          finished = true;
          const data = message.data;
          record.result =
            data.type === "proposal" ? data.proposal.diff : data.result;
          if (data.type === "proposal") {
            if (request.invalid) {
              record.state = "Stale";
              status(
                "Stale proposal: instruction or selection changed. Your edits were preserved.",
              );
              el("result").textContent = data.proposal.diff;
            } else {
              proposal = {
                ...request,
                replacement: data.proposal.replacement,
                record,
              };
              el("result").textContent =
                data.proposal.explanation + "\n\n" + data.proposal.diff;
              el("apply").disabled = false;
              el("reject").disabled = false;
              record.state = "Awaiting review";
              status("Proposal ready. Review, then accept or reject.");
              if (
                request.live &&
                request.auto &&
                el("live").checked &&
                el("auto-apply").checked
              )
                applyProposal();
            }
          } else {
            el("result").textContent = data.result;
            record.state = "Answered";
            status("Response ready.");
          }
        }
      }
      if (done) break;
    }
    if (!finished)
      throw new Error("Stream ended before completion. Input preserved.");
  } catch (err) {
    if (active === request) {
      record.state = err.name === "AbortError" ? "Cancelled" : "Failed";
      status(
        err.name === "AbortError" ? "Cancelled. Input preserved." : err.message,
      );
    }
  } finally {
    if (active === request) {
      active = null;
      requestBusy(false);
      renderHistory();
      pump();
    }
  }
}
function applyProposal() {
  const p = proposal;
  if (!p) return;
  const doc = docs.find((d) => d.id === p.docId);
  if (!doc || p.invalid || textOf(doc).slice(p.from, p.to) !== p.original) {
    p.record.state = "Stale";
    clearProposal();
    renderHistory();
    status("Stale proposal. Input preserved.");
    return;
  }
  clearProposal();
  if (active?.id === p.id) active = null;
  const spec = {
    changes: { from: p.from, to: p.to, insert: p.replacement },
    annotations: [aiEdit.of(true), isolateHistory.of("full")],
  };
  if (doc === current) view.dispatch(spec);
  else {
    const tr = doc.state.update(spec);
    doc.state = tr.state;
    doc.dirty = true;
    for (const target of pending.filter((t) => t.docId === doc.id))
      Object.assign(target, mapTarget(target, tr.changes));
  }
  p.record.state = "Accepted";
  renderHistory();
  status("Change accepted. Undo restores the original text.");
  requestBusy(!!active);
  pump();
}
el("apply").onclick = applyProposal;
el("reject").onclick = () => {
  if (proposal) proposal.record.state = "Rejected";
  clearProposal();
  renderHistory();
  status("Proposal rejected. Input preserved.");
  pump();
};
function cancelRequest() {
  if (!active) return;
  const r = active;
  active = null;
  r.record.state = "Cancelled";
  r.controller.abort();
  fetch("/api/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ request_id: r.id }),
  }).catch(() => {});
  pending.length = 0;
  requestBusy(false);
  renderHistory();
  status("Cancelled. Input preserved.");
}
el("cancel").onclick = cancelRequest;
function renderHistory() {
  el("history-list").replaceChildren();
  if (!records.length) el("history-list").textContent = "No requests yet.";
  for (const record of records) {
    const card = document.createElement("details");
    card.className = "history-card";
    const summary = document.createElement("summary");
    summary.textContent = `${record.time} · ${record.action} · ${record.document} · ${record.state}`;
    const prompt = document.createElement("p");
    prompt.textContent = record.instruction || "Selection action";
    const result = document.createElement("pre");
    result.textContent = record.result;
    const context = document.createElement("details"),
      label = document.createElement("summary"),
      pre = document.createElement("pre");
    label.textContent = "Sources and context snapshot";
    pre.textContent = record.context;
    context.append(label, pre);
    card.append(summary, prompt, result, context);
    el("history-list").append(card);
  }
}
async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    status("Copied.");
  } catch {
    status("Clipboard unavailable. Select the text and copy it.");
  }
}
el("copy").onclick = () => copy(textOf(current));
el("copy-result").onclick = () => copy(el("result").textContent);
el("download").onclick = () => {
  const url = URL.createObjectURL(
      new Blob([textOf(current)], { type: "text/plain;charset=utf-8" }),
    ),
    a = document.createElement("a");
  a.href = url;
  a.download = current.name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status("Document downloaded.");
};
window.addEventListener("beforeunload", (e) => {
  if (docs.some((d) => d.dirty) || sources.length) {
    e.preventDefault();
    e.returnValue = "";
  }
});
Vim.defineEx("write", "w", () => el("download").click());
newDocument();
renderSources();
