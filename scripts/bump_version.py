#!/usr/bin/env python3
"""
Version management script for AIVim Editor.

This script handles version bumping and ensures consistency across:
- pyproject.toml
- VERSION file
- aivim/__init__.py (if __version__ exists)

Usage:
    python scripts/bump_version.py [major|minor|patch|<version>]

Examples:
    python scripts/bump_version.py patch    # 0.5.1 -> 0.5.2
    python scripts/bump_version.py minor    # 0.5.1 -> 0.6.0
    python scripts/bump_version.py major    # 0.5.1 -> 1.0.0
    python scripts/bump_version.py 1.2.3    # Set to specific version
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Tuple


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """
    Parse a semantic version string into major, minor, patch components.

    Args:
        version_str: Version string in format "major.minor.patch"

    Returns:
        Tuple of (major, minor, patch) as integers

    Raises:
        ValueError: If version string is invalid
    """
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str.strip())
    if not match:
        raise ValueError(f"Invalid version format: {version_str}. Expected: major.minor.patch")

    return tuple(map(int, match.groups()))


def format_version(major: int, minor: int, patch: int) -> str:
    """
    Format version components into a semantic version string.

    Args:
        major: Major version number
        minor: Minor version number
        patch: Patch version number

    Returns:
        Version string in format "major.minor.patch"
    """
    return f"{major}.{minor}.{patch}"


def bump_version(current_version: str, bump_type: str) -> str:
    """
    Bump version according to semantic versioning rules.

    Args:
        current_version: Current version string
        bump_type: One of 'major', 'minor', or 'patch'

    Returns:
        New version string

    Raises:
        ValueError: If bump_type is invalid
    """
    major, minor, patch = parse_version(current_version)

    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Expected: major, minor, or patch")

    return format_version(major, minor, patch)


def read_version_from_file(file_path: Path) -> str:
    """
    Read version from VERSION file.

    Args:
        file_path: Path to VERSION file

    Returns:
        Version string

    Raises:
        FileNotFoundError: If VERSION file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"VERSION file not found at {file_path}")

    return file_path.read_text().strip()


def update_version_file(file_path: Path, new_version: str) -> None:
    """
    Update VERSION file with new version.

    Args:
        file_path: Path to VERSION file
        new_version: New version string
    """
    file_path.write_text(f"{new_version}\n")
    print(f"✓ Updated {file_path.name}: {new_version}")


def update_pyproject_toml(file_path: Path, new_version: str) -> None:
    """
    Update version in pyproject.toml.

    Args:
        file_path: Path to pyproject.toml
        new_version: New version string
    """
    content = file_path.read_text()
    pattern = r'version = "[^"]*"'
    replacement = f'version = "{new_version}"'

    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        raise ValueError("Could not find version field in pyproject.toml")

    file_path.write_text(new_content)
    print(f"✓ Updated {file_path.name}: {new_version}")


def update_init_file(file_path: Path, new_version: str) -> None:
    """
    Update __version__ in __init__.py if it exists.

    Args:
        file_path: Path to __init__.py
        new_version: New version string
    """
    if not file_path.exists():
        print(f"⚠ Skipping {file_path.name}: File not found")
        return

    content = file_path.read_text()
    pattern = r'__version__\s*=\s*["\'][^"\']*["\']'
    replacement = f'__version__ = "{new_version}"'

    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        print(f"⚠ Skipping {file_path.name}: No __version__ attribute found")
        return

    file_path.write_text(new_content)
    print(f"✓ Updated {file_path.name}: {new_version}")


def validate_version_consistency(
    version_file: Path,
    pyproject_file: Path,
    init_file: Path
) -> bool:
    """
    Validate that versions are consistent across all files.

    Args:
        version_file: Path to VERSION file
        pyproject_file: Path to pyproject.toml
        init_file: Path to __init__.py

    Returns:
        True if all versions are consistent, False otherwise
    """
    # Read VERSION file
    file_version = read_version_from_file(version_file)

    # Read pyproject.toml
    pyproject_content = pyproject_file.read_text()
    pyproject_match = re.search(r'version = "([^"]*)"', pyproject_content)
    if not pyproject_match:
        print("✗ Could not find version in pyproject.toml")
        return False
    pyproject_version = pyproject_match.group(1)

    # Check consistency
    versions = {'VERSION': file_version, 'pyproject.toml': pyproject_version}

    # Read __init__.py if it exists
    if init_file.exists():
        init_content = init_file.read_text()
        init_match = re.search(r'__version__\s*=\s*["\']([^"\']*)["\']', init_content)
        if init_match:
            versions['__init__.py'] = init_match.group(1)

    # Check if all versions are the same
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        print("✗ Version mismatch detected:")
        for file, version in versions.items():
            print(f"  {file}: {version}")
        return False

    print(f"✓ All versions are consistent: {file_version}")
    return True


def main():
    """Main entry point for the version management script."""
    parser = argparse.ArgumentParser(
        description='Bump version for AIVim Editor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'bump_type',
        nargs='?',
        default='patch',
        help='Version bump type: major, minor, patch, or specific version (e.g., 1.2.3)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate version consistency without making changes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent
    version_file = project_root / 'VERSION'
    pyproject_file = project_root / 'pyproject.toml'
    init_file = project_root / 'aivim' / '__init__.py'

    # Validate only mode
    if args.validate:
        is_valid = validate_version_consistency(version_file, pyproject_file, init_file)
        sys.exit(0 if is_valid else 1)

    try:
        # Read current version
        current_version = read_version_from_file(version_file)
        print(f"Current version: {current_version}")

        # Determine new version
        if args.bump_type in ('major', 'minor', 'patch'):
            new_version = bump_version(current_version, args.bump_type)
        else:
            # Assume it's a specific version
            new_version = args.bump_type
            # Validate the format
            parse_version(new_version)

        print(f"New version: {new_version}")

        if args.dry_run:
            print("\nDry run mode - no changes made")
            print(f"Would update VERSION file: {new_version}")
            print(f"Would update pyproject.toml: {new_version}")
            print(f"Would update __init__.py: {new_version}")
            return

        # Update all files
        print("\nUpdating version files...")
        update_version_file(version_file, new_version)
        update_pyproject_toml(pyproject_file, new_version)
        update_init_file(init_file, new_version)

        print(f"\n✓ Version bumped successfully: {current_version} -> {new_version}")
        print("\nNext steps:")
        print("1. Review the changes")
        print("2. Commit the changes: git add -A && git commit -m 'Bump version to {}'".format(new_version))
        print("3. Create a git tag: git tag v{}".format(new_version))
        print("4. Push changes: git push && git push --tags")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
