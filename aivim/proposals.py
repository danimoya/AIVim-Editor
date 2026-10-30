"""Strict, atomic snapshot proposals shared by terminal and browser."""
from dataclasses import dataclass
import difflib
import json
from .ai_service import AIError


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Proposal:
    request_id: str
    document_id: str
    base_revision: int
    snapshot: str
    edits: tuple
    explanation: str
    provider: str
    model: str
    def content(self):
        text=self.snapshot
        for e in sorted(self.edits,key=lambda e:e.start,reverse=True): text=text[:e.start]+e.text+text[e.end:]
        return text
    def diff(self): return list(difflib.unified_diff(self.snapshot.splitlines(),self.content().splitlines(),fromfile='original',tofile='proposal',lineterm=''))
    def validate_document(self,tab):
        if tab is None or tab.document_id!=self.document_id or tab.buffer.revision!=self.base_revision or tab.buffer.get_content()!=self.snapshot:
            raise AIError('STALE_PROPOSAL','Document changed; request a fresh proposal')


def validate_edits(raw,snapshot,allowed):
    if not isinstance(raw,list) or len(raw)>1000: raise AIError('INVALID_RESPONSE','Expected a bounded edits array')
    edits=[]
    for item in raw:
        if not isinstance(item,dict) or set(item)!={'start','end','text'}: raise AIError('INVALID_RESPONSE','Invalid edit fields')
        a,b,text=item['start'],item['end'],item['text']
        if type(a) is not int or type(b) is not int or not isinstance(text,str) or not 0<=a<=b<=len(snapshot): raise AIError('INVALID_RESPONSE','Invalid edit coordinates')
        if not any(lo<=a<=b<=hi for lo,hi in allowed): raise AIError('INVALID_RESPONSE','Edit is outside permitted selection')
        if len(text.encode())>1024*1024: raise AIError('INVALID_RESPONSE','Replacement too large')
        edits.append(Edit(a,b,text))
    ordered=sorted(edits,key=lambda e:(e.start,e.end))
    for left,right in zip(ordered,ordered[1:]):
        if left.end>right.start or left.start==right.start: raise AIError('INVALID_RESPONSE','Overlapping edits')
    return tuple(ordered)


def parse_proposal(job,result):
    try: data=json.loads(result.text)
    except (ValueError,TypeError): raise AIError('INVALID_RESPONSE','AI edit response must be valid JSON') from None
    if not isinstance(data,dict):raise AIError('INVALID_RESPONSE','AI edit response must be an object')
    explanation=data.get('explanation','')
    if not isinstance(explanation,str):raise AIError('INVALID_RESPONSE','Invalid explanation')
    if job.action=='nlp':
        if set(data)-{'edits','explanation'}:raise AIError('INVALID_RESPONSE','Unknown proposal fields')
        raw=data.get('edits')
    else:
        if set(data)!={'code','explanation'} or not isinstance(data.get('code'),str):raise AIError('INVALID_RESPONSE','Expected code and explanation strings')
        a,b=job.selected_ranges[0];code=data['code']
        if job.action=='generate' and code:
            if a<len(job.source_snapshot) and not code.endswith('\n'):code+='\n'
            if a==len(job.source_snapshot) and a and not job.source_snapshot.endswith('\n'):code='\n'+code
        raw=[{'start':a,'end':b,'text':code}]
    edits=validate_edits(raw,job.source_snapshot,job.selected_ranges)
    return Proposal(job.request_id,job.document_id,job.base_revision,job.source_snapshot,edits,explanation,result.provider,result.model)
