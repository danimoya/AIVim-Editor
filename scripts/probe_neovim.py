"""Evaluate Neovim RPC embedding in a clean child, without loading user plugins."""
import json
import time
import pynvim
started=time.monotonic()
nvim=pynvim.attach('child',argv=['nvim','--embed','--clean','-u','NONE','-i','NONE'])
try:
    nvim.ui_attach(80,24,rgb=True,ext_linegrid=True)
    nvim.current.buffer[:]=['hello world']
    nvim.command('normal! gg0dw')
    assert nvim.current.buffer[:]==['world']
    nvim.command('undo')
    assert nvim.current.buffer[:]==['hello world']
    print(json.dumps({'rpc_embedding':True,'external_linegrid':True,'vim_motion_and_undo':True,'elapsed_seconds':round(time.monotonic()-started,3)}))
finally:
    try:nvim.command('qa!')
    except (OSError,EOFError):pass
