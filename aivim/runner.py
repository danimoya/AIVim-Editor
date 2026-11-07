"""Explicit bounded subprocess execution, with output and cancellation."""
import os
import signal
import subprocess
import threading
import time


class CommandRun:
    def __init__(self, argv, root, timeout=60):
        self.argv,self.root,self.timeout=argv,root,timeout
        self.output='';self.returncode=None;self.process=None
        self.finished=threading.Event();self.cancelled=threading.Event()

    def cancel(self):
        self.cancelled.set()
        if self.process and self.process.poll() is None:
            try:
                if os.name!='nt':os.killpg(self.process.pid,signal.SIGTERM)
                else:self.process.terminate()
            except ProcessLookupError:pass

    def execute(self):
        try:
            if self.cancelled.is_set():return
            self.process=subprocess.Popen(self.argv,cwd=self.root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                          stdin=subprocess.DEVNULL,start_new_session=os.name!='nt')
            size=0;chunks=[]
            def read():
                nonlocal size
                while True:
                    chunk=self.process.stdout.read(4096)
                    if not chunk:break
                    if size<256*1024:chunks.append(chunk[:256*1024-size]);size+=len(chunk)
            reader=threading.Thread(target=read,daemon=True);reader.start()
            deadline=time.monotonic()+self.timeout
            while self.process.poll() is None:
                if self.cancelled.is_set() or time.monotonic()>deadline:
                    self.cancel()
                    try:self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:self.process.kill()
                    break
                time.sleep(.03)
            self.returncode=self.process.wait(timeout=3);reader.join(timeout=2)
            self.output=b''.join(chunks).decode('utf-8',errors='replace')
            if size>=256*1024:self.output+='\n[Output truncated at 256 KiB]'
            if self.cancelled.is_set():self.output+='\n[Cancelled or timed out]'
        except (OSError,subprocess.TimeoutExpired) as exc:self.output=str(exc);self.returncode=-1
        finally:self.finished.set()
