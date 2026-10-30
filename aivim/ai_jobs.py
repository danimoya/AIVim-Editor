"""Immutable document snapshots. Workers only publish events; UI owns mutations."""
from dataclasses import dataclass, field
import queue
import threading
import time
import uuid
from .ai_service import AIError


@dataclass(frozen=True)
class AIJob:
    document_id: str
    base_revision: int
    source_snapshot: str
    action: str
    provider: str
    model: str
    selected_ranges: tuple
    allowed_context: str
    instruction: str
    deadline: float
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cancellation: threading.Event = field(default_factory=threading.Event,compare=False)


@dataclass(frozen=True)
class AIEvent:
    job: AIJob
    result: object = None
    error: object = None


class AIJobs:
    def __init__(self, service, max_workers=2):
        self.service=service;self.events=queue.Queue();self.active={};self._slots=threading.BoundedSemaphore(max_workers)
    def submit(self, job):
        if not self._slots.acquire(False): raise AIError('BUSY','AI worker capacity reached',True)
        self.active[job.request_id]=job
        def work():
            try:
                source=job.source_snapshot
                if job.action in ('improve','explain','analyze'):
                    start,end=job.selected_ranges[0];source=source[start:end]
                result=self.service.request(job.action,source,job.allowed_context,job.instruction,provider=job.provider,model=job.model,request_id=job.request_id,cancel=job.cancellation)
                self.events.put(AIEvent(job,result=result))
            except AIError as exc: self.events.put(AIEvent(job,error=exc))
            except Exception: self.events.put(AIEvent(job,error=AIError('UPSTREAM','AI worker failed')))
            finally: self._slots.release()
        threading.Thread(target=work,daemon=True,name='aivim-ai-'+job.request_id[:8]).start()
        return job.request_id
    def cancel(self, request_id):
        job=self.active.pop(request_id,None)
        if job: job.cancellation.set()
    def cancel_document(self, document_id):
        for rid,job in list(self.active.items()):
            if job.document_id==document_id:self.cancel(rid)
    def drain(self):
        for rid,job in list(self.active.items()):
            if time.monotonic() >= job.deadline:
                self.cancel(rid);yield AIEvent(job,error=AIError('TIMEOUT','AI deadline exceeded',True))
        while True:
            try:event=self.events.get_nowait()
            except queue.Empty:break
            if event.job.request_id not in self.active or event.job.cancellation.is_set():continue
            self.active.pop(event.job.request_id);yield event
    def close(self):
        for rid in list(self.active):self.cancel(rid)
