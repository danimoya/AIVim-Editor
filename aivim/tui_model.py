"""Terminal workspace state, independent of rendering and provider transports."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
import threading
import uuid

from .file_store import FileIdentity


@dataclass
class Document:
    name: str
    content: str = ""
    saved: str = ""
    identity: FileIdentity | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    live_from: int | None = None

    @property
    def dirty(self):
        return self.content != self.saved


@dataclass
class Source:
    name: str
    content: str
    path: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class Request:
    document_id: str
    start: int
    end: int
    original: str
    action: str
    instruction: str
    context: str
    provider: str
    model: str
    live: bool = False
    auto: bool = False
    invalid: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cancel: threading.Event = field(default_factory=threading.Event)
    job: object = None
    replacement: str | None = None
    state: str = "Queued"
    result: str = ""


def offset(text, location):
    row, column = location
    lines = text.split("\n")
    row = max(0, min(row, len(lines) - 1))
    return sum(len(line) + 1 for line in lines[:row]) + min(column, len(lines[row]))


def location(text, index):
    index = max(0, min(index, len(text)))
    before = text[:index]
    return before.count("\n"), len(before.rsplit("\n", 1)[-1])


def changed_span(before, after):
    """Find one conservative edit enclosing all differences in a Changed message."""
    start = 0
    limit = min(len(before), len(after))
    while start < limit and before[start] == after[start]:
        start += 1
    end_before, end_after = len(before), len(after)
    while (
        end_before > start and end_after > start and before[end_before - 1] == after[end_after - 1]
    ):
        end_before -= 1
        end_after -= 1
    return start, end_before, end_after - start


def map_position(pos, start, end, inserted, right=False):
    if pos < start or (pos == start and not right):
        return pos
    if pos >= end:
        return pos + inserted - (end - start)
    return start + (inserted if right else 0)


def map_request(request, start, end, inserted):
    touched = (
        (request.start <= start <= request.end)
        if start == end
        else (start < request.end and end > request.start)
    )
    request.invalid |= touched
    request.start = map_position(request.start, start, end, inserted, True)
    request.end = map_position(request.end, start, end, inserted, False)


def completed_block(text, start, head):
    if start is None or start > head:
        return None
    value = text[start:head]
    match = re.search(r"\n[ \t]*\n[ \t]*$", value)
    if not match or not value[: match.start()].strip():
        return None
    return start, start + match.start(), value[: match.start()]


def partial_code(raw):
    """Show only a complete JSON string prefix; never apply this preview."""
    match = re.search(r'"code"\s*:\s*"', raw)
    if not match:
        return "Generating…"
    encoded = []
    escaped = False
    for char in raw[match.end() :]:
        if char == '"' and not escaped:
            break
        encoded.append(char)
        escaped = not escaped if char == "\\" else False
    value = "".join(encoded)
    # A partial JSON escape contains at most six characters.
    for trim in range(min(7, len(value) + 1)):
        try:
            return json.loads('"' + (value[:-trim] if trim else value) + '"')
        except ValueError:
            pass
    return "Generating…"
