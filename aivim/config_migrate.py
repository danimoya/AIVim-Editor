"""Explicit settings migration; keeps originals and never copies credentials."""
import argparse
from pathlib import Path
from .settings import Settings


def migrate(source,destination):
    source=Path(source).expanduser();destination=Path(destination).expanduser()
    if source.resolve()==destination.resolve() or destination.exists():raise ValueError('Choose a new destination; legacy files are preserved')
    settings=Settings(str(source))
    if not settings.loaded:raise ValueError('No source configuration found')
    if not settings.save(str(destination)):raise ValueError('Configuration migration failed')
    return destination


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('destination');args=parser.parse_args();migrate(args.source,args.destination)
if __name__=='__main__':main()
