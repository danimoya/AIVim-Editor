"""Bounded project context and reviewed, recoverable filesystem change sets."""
from __future__ import annotations
from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
from .file_store import FileStore, FileIdentity
from .session import SessionStore

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist', 'build'}


def digest(text): return hashlib.sha256(text.encode()).hexdigest()


class Project:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir(): raise ValueError('Choose an existing project folder.')
        self.store = FileStore()

    def path(self, relative):
        raw = Path(relative)
        if raw.is_absolute() or '..' in raw.parts or not raw.parts:
            raise ValueError('Use a relative project path without traversal.')
        path = (self.root / raw).resolve()
        if not path.is_relative_to(self.root) or path == self.root: raise ValueError('Path escapes project.')
        if any(p in EXCLUDED for p in raw.parts) or raw.name.startswith('.env') or raw.suffix.lower() in {'.pem','.key','.p12','.pfx'}:
            raise ValueError('Generated/private paths are excluded from project context.')
        return path

    def files(self):
        try:
            result = subprocess.run(['git','-C',str(self.root),'ls-files','-z','--cached','--others','--exclude-standard'], capture_output=True, timeout=5)
            names = result.stdout.decode('utf-8').split('\0') if result.returncode == 0 else []
        except (OSError, subprocess.TimeoutExpired): names = []
        if not names:
            for directory, dirs, files in os.walk(self.root):
                dirs[:] = [d for d in dirs if d not in EXCLUDED and not d.startswith('.')]
                names.extend(str((Path(directory)/f).relative_to(self.root)) for f in files)
                if len(names) >= 10000: break
        output = []
        for name in sorted(set(names)):
            if not name: continue
            try:
                path = self.path(name)
                if path.is_file() and path.stat().st_size <= 256*1024: output.append(name)
            except (ValueError, OSError): pass
            if len(output) >= 2000: break
        return output

    def search(self, query):
        """Return explicit candidate chunks; no model or network is involved."""
        terms = query.casefold().split(); output=[]; budget=10*1024*1024
        if not terms: return output
        for name in self.files():
            try:
                raw=self.path(name).read_bytes(); budget-=len(raw)
                if budget<0: break
                if b'\0' in raw: continue
                text=raw.decode('utf-8'); lines=text.splitlines()
            except (OSError, UnicodeError): continue
            path_match=all(term in name.casefold() for term in terms)
            hits=[i for i,line in enumerate(lines) if all(term in line.casefold() for term in terms)]
            if path_match and not hits: hits=[0]
            last_end=-1
            for at in hits[:5]:
                start=max(0,at-3);end=min(len(lines),at+12)
                if start<=last_end: continue
                last_end=end
                output.append({'path':name,'start':start+1,'end':end,'text':'\n'.join(lines[start:end]),'digest':hashlib.sha256(raw).hexdigest()})
                if len(output)>=100:return output
        return output

    def snapshots(self, names):
        data={}
        for name in names:
            loaded=self.store.load(self.path(name))
            if not loaded: raise ValueError(loaded.message)
            data[name]=loaded
        return data


@dataclass
class FileChange:
    path: str
    before: str
    after: str
    identity: FileIdentity

    def hunks(self):
        return [op for op in difflib.SequenceMatcher(None,self.before.splitlines(True),self.after.splitlines(True),autojunk=True).get_opcodes() if op[0]!='equal']

    def selected_content(self, indexes):
        before=self.before.splitlines(True);after=self.after.splitlines(True);out=[];cursor=0
        for n,(_,a,b,c,d) in enumerate(self.hunks()):
            out.extend(before[cursor:a]);out.extend(after[c:d] if n in indexes else before[a:b]);cursor=b
        out.extend(before[cursor:]);return ''.join(out)

    def diff(self): return ''.join(difflib.unified_diff(self.before.splitlines(True),self.after.splitlines(True),fromfile=self.path,tofile=self.path+' (proposed)'))


class ChangeSet:
    def __init__(self, project, changes):
        self.project,self.changes=project,changes
        self.checkpoint=None

    @classmethod
    def parse(cls, project, response, snapshots):
        data=json.loads(response)
        if not isinstance(data,dict) or set(data)!={'files'} or not isinstance(data['files'],list) or not 1<=len(data['files'])<=20:
            raise ValueError('Expected {"files":[{"path":"relative/path","content":"full text"}]} (1–20 files).')
        changes=[];seen=set();size=0
        for f in data['files']:
            if not isinstance(f,dict) or set(f)!={'path','content'} or not all(isinstance(v,str) for v in f.values()):raise ValueError('Invalid file change.')
            path=project.path(f['path']);name=str(path.relative_to(project.root))
            if name in seen:raise ValueError('Duplicate file change.')
            seen.add(name);size+=len(f['content'].encode())
            if size>1024*1024:raise ValueError('Change set exceeds 1 MiB.')
            loaded=snapshots.get(name)
            if loaded is None:
                if path.exists():raise ValueError('Existing file was not included in the approved context: '+name)
                loaded=project.store.load(path)
            changes.append(FileChange(name,loaded.content,f['content'],loaded.identity))
        return cls(project,changes)

    def _journal(self):
        key=digest(str(self.project.root))[:16]
        store=SessionStore(self.project.root/'project-context')
        store.path=store.path.with_name('checkpoint-'+key+'-'+uuid.uuid4().hex+'.json')
        return store

    def apply(self, selected):
        """Preflight all files; checkpoint before writes; compensate on partial failure."""
        planned=[]
        for n,change in enumerate(self.changes):
            indexes={h for f,h in selected if f==n}
            if not indexes:continue
            path=self.project.path(change.path)
            loaded=self.project.store.load(path)
            if not loaded or loaded.identity.digest!=change.identity.digest:raise ValueError('File changed externally: '+change.path)
            planned.append((change,change.selected_content(indexes)))
        if not planned:raise ValueError('Select at least one change.')
        store=self._journal()
        rows=[{'path':c.path,'before':c.before,'after':text,'existed':c.identity.digest is not None,'written':False} for c,text in planned]
        data={'documents':[],'root':str(self.project.root),'state':'prepared','files':rows}
        store.save(data);self.checkpoint=store.path
        try:
            for row,(change,text) in zip(rows,planned):
                path=self.project.path(change.path);path.parent.mkdir(parents=True,exist_ok=True)
                result=self.project.store.save(path,text,change.identity)
                if not result:raise ValueError(result.message)
                row['written']=True;store.save(data)
            data['state']='applied';store.save(data)
        except Exception:
            self.rollback(store.path, partial=True)
            raise
        return store.path

    def rollback(self, checkpoint=None, *, partial=False):
        path=Path(checkpoint or self.checkpoint)
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('root')!=str(self.project.root):raise ValueError('Checkpoint belongs to a different project.')
        rows=[]
        for r in data['files']:
            observed=self.project.store.load(self.project.path(r['path']))
            if r['written'] or (data['state']=='prepared' and observed and observed.content==r['after']): rows.append(r)
        current={}
        for row in rows:
            loaded=self.project.store.load(self.project.path(row['path']))
            if not loaded or loaded.content!=row['after']:raise ValueError('Rollback refused: file has newer edits: '+row['path'])
            current[row['path']]=loaded
        for row in reversed(rows):
            target=self.project.path(row['path'])
            if row['existed']:
                result=self.project.store.save(target,row['before'],current[row['path']].identity)
                if not result:raise ValueError(result.message)
            else:target.unlink()
            row['written']=False
            data['state']='rolling back'
            store=self._journal();store.path=path;store.save(data)
        data['state']='rolled back';store=self._journal();store.path=path;store.save(data)
        return len(rows)
