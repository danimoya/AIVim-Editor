#!/usr/bin/env python
"""
Demonstration script for testing the AIVim settings functionality
"""
import os
import json
import tempfile
from pathlib import Path

# Create a test settings file
test_config = {
    "editor": {
        "tabstop": 2,
        "expandtab": False,
        "autoindent": True,
        "number": True,
        "wrap": False
    },
    "display": {
        "theme": "dark",
        "syntax": True
    },
    "ai": {
        "default_model": "claude",
        "timeout": 60
    },
    "search": {
        "ignorecase": False,
        "hlsearch": True
    }
}

# Create a temporary config file
config_dir = Path.home() / '.config' / 'aivim'
config_dir.mkdir(parents=True, exist_ok=True)
config_file = config_dir / 'test_settings.json'

print("Creating test settings file at:", config_file)
with open(config_file, 'w') as f:
    json.dump(test_config, f, indent=2)

# Test the settings module directly
from aivim.settings import Settings

print("\n=== Testing Settings Module ===")

# Test loading settings
settings = Settings(config_path=str(config_file))
print(f"Loaded settings from: {settings.config_path}")

# Test getting settings
print(f"\nTabstop: {settings.get('tabstop')}")
print(f"Expand tab: {settings.get('expandtab')}")
print(f"Theme: {settings.get('theme')}")
print(f"Default AI model: {settings.get('default_model')}")

# Test aliases
print(f"\nTabstop (using 'ts' alias): {settings.get('ts')}")
print(f"Expand tab (using 'et' alias): {settings.get('et')}")

# Test setting values
print("\n=== Testing Set Operations ===")
settings.set('tabstop', 8)
print(f"Changed tabstop to: {settings.get('tabstop')}")

settings.toggle('expandtab')
print(f"Toggled expandtab to: {settings.get('expandtab')}")

# Test save
new_config_file = config_dir / 'test_settings_saved.json'
if settings.save(str(new_config_file)):
    print(f"\nSaved settings to: {new_config_file}")
    with open(new_config_file, 'r') as f:
        saved_data = json.load(f)
        print("Saved data sample:")
        print(f"  editor.tabstop: {saved_data['editor']['tabstop']}")
        print(f"  editor.expandtab: {saved_data['editor']['expandtab']}")

# Test help
print("\n=== Settings Help (first 10 lines) ===")
help_lines = settings.get_help()
for line in help_lines[:10]:
    print(line)

print("\n=== Demo Complete ===")
print("\nYou can now test the settings in AIVim by:")
print("1. Running: python -m aivim.run_editor")
print("2. Press ':' to enter command mode")
print("3. Try these commands:")
print("   :set?            - Show settings help")
print("   :set all         - Show all settings")
print("   :set tabstop     - Show tabstop value")
print("   :set tabstop=8   - Set tabstop to 8")
print("   :set expandtab!  - Toggle expandtab")
print("   :set noexpandtab - Turn off expandtab")
print("   :source " + str(config_file) + " - Load test config")

# Clean up (optional)
# os.unlink(config_file)
# os.unlink(new_config_file)