"""
Code snippets plugin for AIVim

Provides snippet expansion functionality for common code patterns.
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Callable, List, Optional

from ..base import Plugin

logger = logging.getLogger(__name__)


class SnippetsPlugin(Plugin):
    """
    Code snippets plugin

    Features:
    - Define snippets in JSON files
    - Expand snippets with <Tab>
    - Multiple snippet sets per language
    - Variable substitution in snippets
    - Cursor position markers

    Example snippet file (~/.aivim/snippets/python.json):
    {
        "class": {
            "prefix": "class",
            "body": [
                "class ${1:ClassName}:",
                "    \"\"\"${2:Docstring}\"\"\"",
                "    ",
                "    def __init__(self${3:, args}):",
                "        ${4:pass}"
            ],
            "description": "Python class template"
        }
    }
    """

    def get_name(self) -> str:
        return "snippets"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Code snippet expansion for common patterns"

    def get_author(self) -> str:
        return "AIVim Team"

    def initialize(self, editor):
        """Initialize plugin"""
        self.editor = editor
        self.snippets: Dict[str, Dict] = {}
        self.snippet_dirs = [
            Path.home() / ".aivim" / "snippets",
            Path.home() / ".config" / "aivim" / "snippets",
        ]

        # Load snippets
        self._load_all_snippets()

        logger.info(f"Snippets plugin initialized with {len(self.snippets)} snippet sets")

    def get_commands(self) -> Dict[str, Callable]:
        """Get plugin commands"""
        return {
            "snippets-list": self.cmd_list_snippets,
            "snippets-reload": self.cmd_reload_snippets,
            "snippets-expand": self.cmd_expand_snippet,
        }

    def get_keybindings(self) -> Dict[str, Callable]:
        """Get plugin keybindings"""
        return {
            "<Tab>": self.try_expand_snippet,
        }

    def _load_all_snippets(self):
        """Load all snippet files"""
        for snippet_dir in self.snippet_dirs:
            if not snippet_dir.exists():
                continue

            for snippet_file in snippet_dir.glob("*.json"):
                try:
                    language = snippet_file.stem
                    with open(snippet_file, 'r') as f:
                        snippets = json.load(f)

                    self.snippets[language] = snippets
                    logger.debug(f"Loaded {len(snippets)} snippets for {language}")

                except Exception as e:
                    logger.error(f"Failed to load snippets from {snippet_file}: {e}")

    def try_expand_snippet(self, args: str = "") -> bool:
        """
        Try to expand snippet at cursor position

        Returns:
            True if snippet was expanded, False otherwise
        """
        # Get current line and word before cursor
        current_line = self.editor.buffer.lines[self.editor.cursor_y]
        word_start = self.editor.cursor_x

        # Find word boundary
        while word_start > 0 and current_line[word_start - 1].isalnum():
            word_start -= 1

        prefix = current_line[word_start:self.editor.cursor_x]

        if not prefix:
            return False

        # Detect language from file extension
        language = self._detect_language()

        if language not in self.snippets:
            return False

        # Find matching snippet
        for snippet_name, snippet_data in self.snippets[language].items():
            if snippet_data.get('prefix') == prefix:
                self._expand_snippet(snippet_data, word_start)
                return True

        return False

    def _expand_snippet(self, snippet_data: Dict, start_pos: int):
        """
        Expand a snippet

        Args:
            snippet_data: Snippet definition
            start_pos: Start position in line
        """
        body = snippet_data.get('body', [])
        if isinstance(body, str):
            body = [body]

        # Get current line
        current_line = self.editor.buffer.lines[self.editor.cursor_y]

        # Replace prefix with first line of snippet
        if body:
            # Process variables in first line
            first_line = self._process_snippet_line(body[0])
            new_line = current_line[:start_pos] + first_line + current_line[self.editor.cursor_x:]
            self.editor.buffer.lines[self.editor.cursor_y] = new_line

            # Insert additional lines
            for i, line in enumerate(body[1:], 1):
                processed_line = self._process_snippet_line(line)
                # Get indentation from first line
                indent = len(current_line) - len(current_line.lstrip())
                self.editor.buffer.lines.insert(
                    self.editor.cursor_y + i,
                    ' ' * indent + processed_line
                )

            # Move cursor to first variable position
            self._move_to_first_variable()

            logger.debug(f"Expanded snippet: {snippet_data.get('description', 'unnamed')}")

    def _process_snippet_line(self, line: str) -> str:
        """
        Process snippet line, handling variables

        Args:
            line: Snippet line with variables like ${1:default}

        Returns:
            Processed line with variables replaced
        """
        import re

        # Replace ${n:default} with default
        # User can then tab through positions
        def replace_var(match):
            return match.group(2) if match.group(2) else ""

        processed = re.sub(r'\$\{(\d+):([^}]*)\}', replace_var, line)
        # Also handle simple ${n} variables
        processed = re.sub(r'\$\{(\d+)\}', '', processed)

        return processed

    def _move_to_first_variable(self):
        """Move cursor to first variable position"""
        # For now, just move to end of inserted text
        # Full implementation would track variable positions
        pass

    def _detect_language(self) -> str:
        """
        Detect language from file extension

        Returns:
            Language name (e.g., 'python', 'javascript')
        """
        if not self.editor.filename:
            return "text"

        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown',
            '.sh': 'bash',
        }

        ext = Path(self.editor.filename).suffix
        return ext_map.get(ext, 'text')

    def cmd_list_snippets(self, args: str):
        """
        List available snippets

        Args:
            args: Optional language filter
        """
        language = args.strip() or self._detect_language()

        if language not in self.snippets:
            self.editor.status_message = f"No snippets for language: {language}"
            return

        snippets = self.snippets[language]

        # Create snippet list in new tab
        lines = [f"Snippets for {language}", "=" * 50, ""]

        for name, data in snippets.items():
            prefix = data.get('prefix', name)
            desc = data.get('description', 'No description')
            lines.append(f"{prefix:20} - {desc}")

        self.editor.create_tab(f"Snippets: {language}", temporary=True)
        self.editor.buffer.set_lines(lines)
        self.editor.mode = "NORMAL"

        logger.debug(f"Listed {len(snippets)} snippets for {language}")

    def cmd_reload_snippets(self, args: str):
        """Reload all snippet files"""
        self.snippets.clear()
        self._load_all_snippets()

        total_snippets = sum(len(s) for s in self.snippets.values())
        self.editor.status_message = (
            f"Reloaded {total_snippets} snippets "
            f"for {len(self.snippets)} languages"
        )

        logger.info("Snippets reloaded")

    def cmd_expand_snippet(self, args: str):
        """
        Manually expand snippet by name

        Args:
            args: Snippet name
        """
        if not args:
            self.editor.status_message = "Usage: :snippets-expand <name>"
            return

        language = self._detect_language()

        if language not in self.snippets:
            self.editor.status_message = f"No snippets for language: {language}"
            return

        snippet_name = args.strip()

        if snippet_name not in self.snippets[language]:
            self.editor.status_message = f"Snippet not found: {snippet_name}"
            return

        snippet_data = self.snippets[language][snippet_name]
        self._expand_snippet(snippet_data, self.editor.cursor_x)

        logger.debug(f"Manually expanded snippet: {snippet_name}")

    def get_config_schema(self) -> Dict:
        """Get configuration schema"""
        return {
            'snippet_dirs': {
                'type': 'list',
                'default': ['~/.aivim/snippets', '~/.config/aivim/snippets'],
                'description': 'Directories to search for snippet files'
            },
        }

    def configure(self, config: Dict):
        """Configure plugin"""
        if 'snippet_dirs' in config:
            self.snippet_dirs = [Path(d).expanduser() for d in config['snippet_dirs']]
            self._load_all_snippets()
