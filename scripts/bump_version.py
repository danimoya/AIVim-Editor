"""Manage and validate the single version authority and its VERSION mirror."""
import argparse
import ast
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def version():
    tree=ast.parse((ROOT/'aivim/_version.py').read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('bump',nargs='?');parser.add_argument('--validate',action='store_true');args=parser.parse_args()
    current=version()
    if args.validate:
        assert (ROOT/'VERSION').read_text().strip()==current,'VERSION mismatch'
        assert 'version = {attr = "aivim._version.__version__"}' in (ROOT/'pyproject.toml').read_text(),'Build authority mismatch'
        assert 'from ._version import __version__' in (ROOT/'aivim/__init__.py').read_text(),'Runtime authority mismatch'
        print('Versions agree:',current);return
    if not args.bump:parser.error('Supply a version or --validate')
    parts=list(map(int,current.split('.')))
    if args.bump in ('major','minor','patch'):
        index=('major','minor','patch').index(args.bump);parts[index]+=1
        for i in range(index+1,3):parts[i]=0
        new='.'.join(map(str,parts))
    else:new=args.bump
    if not re.fullmatch(r'\d+\.\d+\.\d+',new):parser.error('Expected semantic version')
    (ROOT/'aivim/_version.py').write_text('__version__ = '+repr(new)+'\n');(ROOT/'VERSION').write_text(new+'\n')
if __name__=='__main__':main()
