"""Compatibility entrypoint; packaged factory is authoritative."""
from aivim.web.app import create_app, main
app=create_app()
if __name__=='__main__':main()
