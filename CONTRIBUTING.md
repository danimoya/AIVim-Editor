# Contributing to AIVim

Thank you for your interest in contributing to AIVim! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)
- [Code Style](#code-style)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the Repository**
   ```bash
   # Click the "Fork" button on GitHub
   git clone https://github.com/YOUR_USERNAME/AIVim-Editor.git
   cd AIVim-Editor
   ```

2. **Add Upstream Remote**
   ```bash
   git remote add upstream https://github.com/danimoya/AIVim-Editor.git
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Install Dependencies

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in editable mode with all dev dependencies
pip install -e ".[dev]"

# Or install from requirements.txt
pip install -r requirements.txt
```

### Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Set up git hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-vim-motions` - New features
- `fix/crash-on-empty-file` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/cleanup-ai-service` - Code refactoring
- `test/add-buffer-tests` - Test improvements

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

Detailed explanation of the change (optional)

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(ai-service): add support for Claude API
fix(editor): resolve crash when opening large files
docs(readme): update installation instructions
test(buffer): add tests for multi-line operations
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aivim --cov-report=html

# Run specific test file
pytest tests/test_buffer.py

# Run tests matching a pattern
pytest -k "test_insert"

# Run tests in parallel (faster)
pytest -n auto
```

### Writing Tests

Tests are located in the `tests/` directory and use pytest:

```python
import pytest
from aivim.buffer import Buffer

def test_insert_text():
    """Test inserting text into buffer"""
    buffer = Buffer()
    buffer.insert_text(0, 0, "Hello")
    assert buffer.get_line(0) == "Hello"

def test_buffer_with_fixture(mock_ai_service):
    """Test using a fixture"""
    # Fixtures are defined in tests/conftest.py
    pass
```

### Test Coverage

We aim for at least 70% test coverage. Current coverage:

- Run `pytest --cov=aivim --cov-report=term-missing` to see coverage
- Focus on testing critical paths and edge cases
- Security-related code should have high coverage

### Manual Testing

Before submitting a PR:

1. Test the terminal interface: `python -m aivim.run_editor test_file.py`
2. Test the web interface: `python main.py` (if applicable)
3. Test on your target platform (Linux/macOS/Windows)
4. Test with different Python versions (3.8, 3.9, 3.10, 3.11, 3.12)

## Submitting Changes

### Before Submitting

1. **Run Tests**: Ensure all tests pass
   ```bash
   pytest
   ```

2. **Run Linters**: Fix any linting issues
   ```bash
   # Format code
   black aivim tests
   isort aivim tests

   # Check for errors
   flake8 aivim
   mypy aivim
   pylint aivim
   ```

3. **Run Security Checks**:
   ```bash
   bandit -r aivim
   safety check
   ```

4. **Update Documentation**: If you changed functionality, update relevant docs

5. **Add Tests**: If you added features, add corresponding tests

### Pull Request Process

1. **Push Your Changes**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Go to GitHub and create a PR from your fork
   - Fill out the PR template completely
   - Link any related issues

3. **PR Requirements**
   - All CI checks must pass (tests, linting, security)
   - At least one approving review
   - No merge conflicts
   - Up-to-date with main branch

4. **Review Process**
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Be patient and responsive

5. **Merging**
   - Once approved, a maintainer will merge your PR
   - Your changes will be included in the next release

### Pull Request Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added (if applicable)
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

## Release Process

### For Maintainers

1. **Update Version**
   ```bash
   # Update version in pyproject.toml, VERSION, and aivim/__init__.py
   python scripts/bump_version.py --type minor  # or major, patch
   ```

2. **Update Changelog**
   - Document all changes since last release
   - Follow [Keep a Changelog](https://keepachangelog.com/) format

3. **Create Release PR**
   ```bash
   git checkout -b release/v0.6.0
   # Commit version bumps and changelog
   git push origin release/v0.6.0
   # Create PR to main
   ```

4. **Create GitHub Release**
   - After PR is merged, create a new release on GitHub
   - Tag format: `v0.6.0`
   - Copy changelog content to release notes
   - Publishing the release triggers automatic PyPI deployment

5. **Verify Deployment**
   - Check PyPI for new version: https://pypi.org/project/aivim/
   - Test installation: `pip install aivim==0.6.0`
   - Verify package works correctly

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 0.5.0 → 0.6.0)
- **PATCH**: Bug fixes, backward compatible (e.g., 0.5.0 → 0.5.1)

## Code Style

### Python Style Guide

We follow [PEP 8](https://peps.python.org/pep-0008/) with some modifications:

- **Line Length**: 100 characters (configured in tools)
- **Imports**: Sorted with `isort`
- **Formatting**: Use `black` for automatic formatting
- **Type Hints**: Encouraged but not required
- **Docstrings**: Use Google-style docstrings

### Example Code Style

```python
"""Module docstring explaining the module purpose."""

import os
import sys
from typing import Optional, List

from aivim.buffer import Buffer


class Editor:
    """Brief description of the class.

    Longer description with more details about the class
    and its usage.

    Attributes:
        buffer: The text buffer being edited
        cursor_position: Current cursor location (row, col)
    """

    def __init__(self, filename: Optional[str] = None):
        """Initialize the editor.

        Args:
            filename: Optional file to open on startup
        """
        self.buffer = Buffer()
        self.cursor_position = (0, 0)

        if filename:
            self.load_file(filename)

    def load_file(self, filename: str) -> bool:
        """Load a file into the buffer.

        Args:
            filename: Path to the file to load

        Returns:
            True if file loaded successfully, False otherwise

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        # Implementation
        pass
```

### Tool Configuration

All style tools are configured in `pyproject.toml`:

- **black**: Code formatter
- **isort**: Import sorter
- **flake8**: Linter (configured in `.flake8`)
- **mypy**: Type checker
- **pylint**: Additional linting
- **bandit**: Security linter

Run all checks:
```bash
# Format
black aivim tests
isort aivim tests

# Lint
flake8 aivim
mypy aivim
pylint aivim

# Security
bandit -r aivim
```

## Questions or Need Help?

- **Documentation**: Check the [README](README.md) first
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Email**: daniel.moya@dimensigon.com

Thank you for contributing to AIVim! 🎉
