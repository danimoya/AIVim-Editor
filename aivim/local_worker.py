"""Optional GGUF inference in a killable, resource-limited child process."""
import hashlib
import multiprocessing
import os
from pathlib import Path
import time
from .ai_service import AIError


def verify_model(path,expected,max_bytes=16*1024**3):
    p=Path(path).expanduser()
    if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected.lower()):raise AIError('MODEL_INTEGRITY','A SHA-256 model digest is required')
    if p.stat().st_size>max_bytes:raise AIError('MODEL_INTEGRITY','Model exceeds resource size limit')
    digest=hashlib.sha256()
    with p.open('rb') as f:
        if f.read(4)!=b'GGUF':raise AIError('MODEL_INTEGRITY','Expected GGUF model')
        f.seek(0)
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=expected.lower():raise AIError('MODEL_INTEGRITY','Model checksum mismatch')
    return str(p)


def infer_child(connection,config,system,prompt):
    try:
        # Native engine diagnostics cannot write into the parent's curses terminal.
        with open(os.devnull,'w') as sink:os.dup2(sink.fileno(),1);os.dup2(sink.fileno(),2)
        from llama_cpp import Llama
        model=Llama(model_path=config['path'],n_ctx=config['context'],n_threads=config['threads'],verbose=False)
        response=model.create_chat_completion(messages=[{'role':'system','content':system},{'role':'user','content':prompt}],max_tokens=config['max_tokens'],temperature=config['temperature'])
        choice=response['choices'][0]
        if choice.get('finish_reason')!='stop':connection.send(('INVALID_RESPONSE','Incomplete local model output'))
        else:connection.send(('OK',choice['message']['content']))
    except ImportError:connection.send(('NOT_CONFIGURED','Install aivim[local-llm] to run native inference'))
    except Exception:connection.send(('LOCAL_FAILED','Local inference failed within its resource limits'))
    finally:connection.close()


def guarded_child(connection,config,system,prompt,worker_target):
    """Bound integrity I/O and inference together, including on cancellation."""
    try:
        from .local_limits import apply
        limits_handle=apply(config['memory_mb'],config['cpu_seconds'])
        config['path']=verify_model(config['path'],config['sha256'],max_bytes=config['memory_mb']*1024**2)
        worker_target(connection,config,system,prompt)
    except AIError as exc:connection.send((exc.code,str(exc)))
    except OSError:connection.send(('MODEL_INTEGRITY','Model cannot be read or verified'))
    except Exception:connection.send(('LOCAL_FAILED','Local worker could not establish its resource limits'))
    finally:connection.close()


class LocalWorker:
    def __init__(self,settings,worker_target=infer_child):self.settings=settings;self.worker_target=worker_target
    def complete(self,system,prompt,timeout,cancel=None):
        s=self.settings
        if cancel and cancel.is_set():raise AIError('CANCELLED','Local inference cancelled')
        deadline=time.monotonic()+timeout
        config={'path':str(Path(s.local_model_path).expanduser()),'sha256':s.local_model_sha256,'memory_mb':s.local_memory_mb,'cpu_seconds':s.local_cpu_seconds,'threads':s.local_threads,'context':s.local_context,'max_tokens':s.max_tokens,'temperature':s.temperature}
        ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe(duplex=False);process=ctx.Process(target=guarded_child,args=(child,config,system,prompt,self.worker_target),daemon=True)
        process.start();child.close()
        try:
            while time.monotonic()<deadline:
                if cancel and cancel.is_set():raise AIError('CANCELLED','Local inference cancelled')
                if parent.poll(min(.05,max(0,deadline-time.monotonic()))):
                    try:code,text=parent.recv()
                    except EOFError:raise AIError('LOCAL_FAILED','Local worker exited unexpectedly') from None
                    if code!='OK':raise AIError(code,text)
                    return text
                if not process.is_alive():raise AIError('LOCAL_FAILED','Local worker exceeded resources or exited')
            raise AIError('TIMEOUT','Local inference deadline exceeded',True)
        finally:
            parent.close()
            if process.is_alive():process.terminate()
            process.join(.5)
            if process.is_alive():process.kill();process.join(.5)
            process.close()
