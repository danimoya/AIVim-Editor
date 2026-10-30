"""Actual curses entrypoint in a disposable pseudo-terminal."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest


@pytest.mark.terminal
@pytest.mark.skipif(os.name=='nt',reason='Windows curses requires a native terminal runner; POSIX PTY is unavailable')
def test_real_terminal_burst_save_resize_and_exit(tmp_path):
    import fcntl
    import pty
    import select
    import struct
    import termios
    path=tmp_path/'document.txt';path.write_bytes(b'');config=tmp_path/'settings.json';config.write_text(json.dumps({'schema_version':1,'file':{'auto_backup':False},'editor':{'autoindent':False}}))
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0))
    env=dict(os.environ,TERM='xterm-256color',LANG='C.UTF-8');env.pop('OPENAI_API_KEY',None);env.pop('ANTHROPIC_API_KEY',None)
    proc=subprocess.Popen([sys.executable,'-m','aivim.run_editor',str(path),'--config',str(config)],stdin=slave,stdout=slave,stderr=slave,env=env);os.close(slave);transcript=bytearray()
    def pump(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            ready,_,_=select.select([master],[],[],.02)
            if ready:
                try:transcript.extend(os.read(master,65536))
                except OSError:break
    try:
        pump(.8);assert proc.poll() is None,transcript.decode(errors='replace')
        text='ABCé界xyz'*125;os.write(master,('i'+text).encode());pump(.4)
        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',25,100,0,0));os.write(master,b'\x1b');pump(.1);os.write(master,b':wq\r');pump(1)
        proc.wait(timeout=5);assert proc.returncode==0,transcript.decode(errors='replace')
        assert path.read_text()==text
        (tmp_path/'terminal-transcript.bin').write_bytes(transcript)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        os.close(master)
