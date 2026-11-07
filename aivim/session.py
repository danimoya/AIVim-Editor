"""Private, atomic recovery snapshots; credentials and AI history are excluded by default."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
from .private_files import restrict


class SessionStore:
    def __init__(self, config_path, *, unique=False, project=None):
        key = hashlib.sha256(str(Path(config_path).resolve()).encode()).hexdigest()[:16]
        self.key, self.unique, self.project = key, unique, project
        name = key + ('-' + uuid.uuid4().hex if unique else '') + '.json'
        self.path = Path('~/.local/state/aivim/sessions').expanduser() / name

    def load(self):
        if self.unique:
            candidates = sorted(self.path.parent.glob(self.key + '*.json'), key=lambda p:p.stat().st_mtime, reverse=True)
            for path in candidates:
                result = self._load(path)
                if result and (self.project is None or result.get("project") == self.project): return result
            return None
        return self._load(self.path)

    def _load(self, path):
        try:
            if path.is_symlink() or path.stat().st_size > 512 * 1024 * 1024:
                return None
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('documents'), list): return None
            if any(not isinstance(d, dict) or not isinstance(d.get('name'), str) or not isinstance(d.get('content'), str) for d in data['documents']): return None
            return data
        except (OSError, ValueError, AttributeError):
            return None

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise OSError('Recovery path must not be a symlink')
        restrict(self.path.parent, directory=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix='.recovery-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                restrict(Path(temporary))
                json.dump({'schema': 1, **data}, f, ensure_ascii=False)
                f.flush(); os.fsync(f.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
