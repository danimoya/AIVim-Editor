from __future__ import annotations
"""Transactional text file boundary. Symlinks are followed, never replaced."""
from dataclasses import dataclass
from pathlib import Path
import errno
import hashlib
import os
import stat
import tempfile
import uuid


@dataclass(frozen=True)
class FileIdentity:
    target: str
    digest: str | None
    encoding: str = 'utf-8'
    newline: str = '\n'
    mode: int = 0o600


@dataclass(frozen=True)
class LoadResult:
    ok: bool
    content: str = ''
    identity: FileIdentity | None = None
    code: str = 'OK'
    message: str = ''
    def __bool__(self): return self.ok


@dataclass(frozen=True)
class SaveResult:
    ok: bool
    identity: FileIdentity | None = None
    code: str = 'OK'
    message: str = ''
    backup: str | None = None
    def __bool__(self): return self.ok


def digest(data): return hashlib.sha256(data).hexdigest()


def failure(exc):
    if isinstance(exc, UnicodeError): return 'ENCODING', 'Text cannot be encoded or decoded with the selected encoding'
    if isinstance(exc, PermissionError): return 'PERMISSION', 'File permission denied'
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC: return 'DISK_FULL', 'Disk full'
    return 'IO_ERROR', 'File operation failed'


class FileStore:
    def load(self, filename, encoding='utf-8', newline='\n'):
        target = Path(filename).expanduser().resolve()
        try:
            if not target.exists():
                return LoadResult(True, identity=FileIdentity(str(target), None, encoding, newline))
            raw = target.read_bytes()
            if b'\x00' in raw: return LoadResult(False, code='BINARY', message='Binary files are not supported')
            enc = 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else encoding
            text = raw.decode(enc)
            convention = '\r\n' if '\r\n' in text else ('\r' if '\r' in text else '\n')
            normalized = text.replace('\r\n', '\n').replace('\r', '\n')
            return LoadResult(True, normalized, FileIdentity(str(target), digest(raw), enc, convention, stat.S_IMODE(target.stat().st_mode)))
        except (OSError, UnicodeError) as exc:
            code, message = failure(exc); return LoadResult(False, code=code, message=message)

    def save(self, filename, content, identity=None, *, force=False, backup_dir=None, encoding='utf-8', newline='\n'):
        target = Path(filename).expanduser().resolve()
        temp = None
        try:
            exists = target.exists()
            current = target.read_bytes() if exists else None
            if identity and identity.target != str(target) and Path(filename).is_symlink():
                return SaveResult(False, code='CONFLICT', message='Symlink target changed; reload before saving')
            expected = identity.digest if identity and identity.target == str(target) else None
            if not force and ((expected is not None and (current is None or digest(current) != expected)) or (expected is None and exists)):
                return SaveResult(False, code='CONFLICT', message='Target changed externally or already exists; reload or use :w!')
            enc = identity.encoding if identity else encoding
            nl = identity.newline if identity else newline
            raw = content.replace('\n', nl).encode(enc)
            mode = stat.S_IMODE(target.stat().st_mode) if exists else 0o600
            backup = None
            if exists and backup_dir:
                directory = Path(backup_dir).expanduser(); directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup = directory / (target.name + '.' + uuid.uuid4().hex + '.bak')
                fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as f: f.write(current); f.flush(); os.fsync(f.fileno())
            fd, temp = tempfile.mkstemp(prefix='.aivim-', dir=target.parent)
            with os.fdopen(fd, 'wb') as f:
                f.write(raw); f.flush()
                if hasattr(os,'fchmod'):os.fchmod(f.fileno(),mode)
                else:os.chmod(temp,mode)
                os.fsync(f.fileno())
            # Recheck after the write/backup, narrowing the external-edit race.
            observed = target.read_bytes() if target.exists() else None
            if not force and observed != current:
                return SaveResult(False, code='CONFLICT', message='Target changed while saving')
            os.replace(temp, target); temp = None
            return SaveResult(True, FileIdentity(str(target), digest(raw), enc, nl, mode), backup=str(backup) if backup else None)
        except (OSError, UnicodeError) as exc:
            code, message = failure(exc); return SaveResult(False, code=code, message=message)
        finally:
            if temp and os.path.exists(temp): os.unlink(temp)
