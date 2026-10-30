"""Syntax guard, including retained historical demos, without executing them."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files=[p for directory in ('aivim','tests','verification','scripts') for p in (root/directory).rglob('*.py')]
for p in files:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
print(f'{len(files)} Python sources parsed successfully')
