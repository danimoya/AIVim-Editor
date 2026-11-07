"""Explicit references to open buffers and recent files, never arbitrary path ingestion."""
from dataclasses import dataclass, replace
from collections import Counter
from pathlib import Path
import re


@dataclass(frozen=True)
class FileReference:
    label: str
    path: str = ''
    document_id: str = ''
    origin: str = 'Recent'

    @property
    def token(self):
        return '@' + ('"' + self.label + '"' if re.search(r'\s', self.label) else self.label)


def mention_prefix(text, cursor):
    match = re.search(r'(?<![\w@])@("[^"\n]*|[^\s@"]*)$', text[:cursor])
    if not match: return None
    return match.start(), cursor, match[1].lstrip('"')


def referenced_files(text, candidates):
    tokens = re.findall(r'(?<![\w@])@(?:"([^"\n]+)"|([^\s@";,]+))', text)
    by_label = {candidate.label: candidate for candidate in candidates}
    result = []
    for a, b in tokens:
        label = a or b
        candidate = by_label.get(label) or by_label.get(label.rstrip('.:!?)]}'))
        if candidate and candidate not in result: result.append(candidate)
    return result


def file_candidates(documents, recent, root=None):
    result = []; seen = set()
    def label(path):
        if root:
            try: return Path(path).relative_to(root).as_posix()
            except ValueError: pass
        return Path(path).as_posix()
    for doc in documents:
        path = doc.identity.target if doc.identity else ''
        name = label(path) if path else doc.name
        result.append(FileReference(name, path, doc.id, 'Open' + (' · unsaved' if doc.dirty else '')))
        if path: seen.add(path)
    for path in recent[:50]:
        if path not in seen:
            result.append(FileReference(label(path), path)); seen.add(path)
    counts = Counter(candidate.label for candidate in result)
    return [replace(c, label=f'{c.label} (buffer {c.document_id[:6]})')
            if counts[c.label] > 1 and not c.path else c for c in result]
