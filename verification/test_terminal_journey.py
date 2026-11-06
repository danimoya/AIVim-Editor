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
    proc=subprocess.Popen([sys.executable,'-m','aivim.run_editor',str(path),'--classic','--config',str(config)],stdin=slave,stdout=slave,stderr=slave,env=env);os.close(slave);transcript=bytearray()
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


@pytest.mark.terminal
@pytest.mark.skipif(os.name=='nt',reason='POSIX PTY unavailable')
def test_textual_terminal_entrypoint_mouse_resize_save_and_exit(tmp_path):
    import fcntl
    import pty
    import select
    import struct
    import termios
    path=tmp_path/'workbench.py';path.write_bytes(b'')
    config=tmp_path/'settings.json';config.write_text(json.dumps({'schema_version':1,'file':{'auto_backup':False}}))
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',42,132,0,0))
    env=dict(os.environ,TERM='xterm-256color',COLORTERM='truecolor',LANG='C.UTF-8')
    for key in ('NO_COLOR','OPENAI_API_KEY','ANTHROPIC_API_KEY'):env.pop(key,None)
    proc=subprocess.Popen([sys.executable,'-m','aivim.run_editor',str(path),'--config',str(config)],stdin=slave,stdout=slave,stderr=slave,env=env)
    os.close(slave);transcript=bytearray()
    def pump(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            ready,_,_=select.select([master],[],[],.02)
            if ready:
                try:transcript.extend(os.read(master,65536))
                except OSError:break
    try:
        pump(1.3);assert proc.poll() is None,transcript.decode(errors='replace')
        assert b'1006h' in transcript
        # F2 opens a real terminal menu. Escape closes it without leaving the editor.
        os.write(master,b'\x1bOQ');pump(.25)
        assert b'Ask about selection' in transcript
        os.write(master,b'\x1b');pump(.1)
        text='ABCé界xyz'*60;os.write(master,('i'+text).encode());pump(1)
        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',40,85,0,0));pump(.3)
        os.write(master,b'\x1b');pump(.1);os.write(master,b'\x13');pump(.3);os.write(master,b'\x11');pump(.8)
        proc.wait(timeout=5)
        assert proc.returncode==0,transcript.decode(errors='replace')
        assert path.read_text()==text
        (tmp_path/'textual-terminal-transcript.bin').write_bytes(transcript)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        os.close(master)
