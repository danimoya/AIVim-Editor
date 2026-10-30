"""Nonblocking Unicode/special-key and bracketed-paste decoder."""
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class Paste:
    text: str

class InputDecoder:
    START='\x1b[200~';END='\x1b[201~'
    def __init__(self):self.pending='';self.since=0;self.paste=None
    def feed(self,key):
        if key==27:key='\x1b'
        if self.paste is not None:
            if isinstance(key,str):
                self.paste+=key
                if self.paste.endswith(self.END):
                    text=self.paste[:-len(self.END)];self.paste=None;return [Paste(text)]
                return []
            # Resize remains an event even during paste; it never consumes buffered text.
            return [key]
        if self.pending:
            if isinstance(key,str) and self.START.startswith(self.pending+key):
                self.pending+=key
                if self.pending==self.START:self.pending='';self.paste=''
                return []
            prior=list(self.pending);self.pending='';return prior+self.feed(key)
        if key=='\x1b':self.pending=key;self.since=time.monotonic();return []
        return [key]
    def flush(self):
        if self.pending and time.monotonic()-self.since>=.025:
            keys=list(self.pending);self.pending='';return keys
        return []
