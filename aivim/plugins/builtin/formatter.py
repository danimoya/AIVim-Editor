"""
Code formatter plugin for AIVim

Provides code formatting and linting for various languages.
"""
import subprocess
import logging
from pathlib import Path
from typing import Dict, Callable, Optional, List

from ..base import Plugin

logger = logging.getLogger(__name__)


class FormatterPlugin(Plugin):
    """
    Code formatter and linter plugin

    Supports:
    - Python: black, autopep8, isort
    - JavaScript/TypeScript: prettier
    - Go: gofmt
    - Rust: rustfmt
    - JSON: jq
    - Auto-format on save (configurable)

    Commands:
    - :format - Format current buffer
    - :format-config - Show formatter configuration
    - :lint - Run linter on current buffer
    """

    def get_name(self) -> str:
        return "formatter"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Code formatting and linting for various languages"

    def get_author(self) -> str:
        return "AIVim Team"

    def initialize(self, editor):
        """Initialize plugin"""
        self.editor = editor

        # Default configuration
        self.config = {
            'auto_format_on_save': False,
            'python_formatter': 'black',  # or 'autopep8'
            'python_line_length': 88,
            'javascript_formatter': 'prettier',
            'use_isort': True,
        }

        # Check which formatters are available
        self.available_formatters = self._check_available_formatters()

        logger.info(
            f"Formatter plugin initialized. "
            f"Available: {', '.join(self.available_formatters)}"
        )

    def get_commands(self) -> Dict[str, Callable]:
        """Get plugin commands"""
        return {
            "format": self.cmd_format,
            "format-config": self.cmd_show_config,
            "lint": self.cmd_lint,
        }

    def configure(self, config: Dict):
        """Configure plugin"""
        self.config.update(config)
        logger.info(f"Formatter configured: {self.config}")

    def on_buffer_save(self, buffer, filename: str):
        """
        Format buffer on save if enabled

        Args:
            buffer: Buffer instance
            filename: Saved filename
        """
        if self.config.get('auto_format_on_save') and filename:
            try:
                self._format_buffer(filename)
                logger.debug(f"Auto-formatted {filename}")
            except Exception as e:
                logger.error(f"Auto-format failed: {e}")

    def cmd_format(self, args: str):
        """
        Format current buffer

        Args:
            args: Optional formatter name override
        """
        if not self.editor.filename:
            self.editor.status_message = "No file to format"
            return

        try:
            formatter = args.strip() if args else None
            self._format_buffer(self.editor.filename, formatter)
            self.editor.status_message = "Buffer formatted successfully"

        except Exception as e:
            self.editor.status_message = f"Format error: {e}"
            logger.error(f"Format failed: {e}")

    def cmd_show_config(self, args: str):
        """Show formatter configuration"""
        lines = ["Formatter Configuration", "=" * 50, ""]

        lines.append("Available Formatters:")
        for formatter in self.available_formatters:
            lines.append(f"  ✓ {formatter}")

        lines.append("")
        lines.append("Current Configuration:")
        for key, value in self.config.items():
            lines.append(f"  {key}: {value}")

        self.editor.create_tab("Formatter Config", temporary=True)
        self.editor.buffer.set_lines(lines)
        self.editor.mode = "NORMAL"

    def cmd_lint(self, args: str):
        """
        Run linter on current buffer

        Args:
            args: Optional linter name override
        """
        if not self.editor.filename:
            self.editor.status_message = "No file to lint"
            return

        try:
            results = self._lint_buffer(self.editor.filename)

            if not results:
                self.editor.status_message = "No linting issues found"
                return

            # Display results in new tab
            lines = ["Lint Results", "=" * 50, ""]
            lines.extend(results)

            self.editor.create_tab("Lint Results", temporary=True)
            self.editor.buffer.set_lines(lines)
            self.editor.mode = "NORMAL"

        except Exception as e:
            self.editor.status_message = f"Lint error: {e}"
            logger.error(f"Lint failed: {e}")

    def _format_buffer(self, filename: str, formatter: Optional[str] = None):
        """
        Format buffer using appropriate formatter

        Args:
            filename: File to format
            formatter: Optional specific formatter to use

        Raises:
            Exception: If formatting fails
        """
        language = self._detect_language(filename)

        if language == 'python':
            self._format_python(filename, formatter)
        elif language in ('javascript', 'typescript'):
            self._format_javascript(filename)
        elif language == 'go':
            self._format_go(filename)
        elif language == 'rust':
            self._format_rust(filename)
        elif language == 'json':
            self._format_json(filename)
        else:
            raise Exception(f"No formatter available for {language}")

        # Reload buffer after formatting
        with open(filename, 'r') as f:
            content = f.read()
        self.editor.buffer.set_lines(content.splitlines())

    def _format_python(self, filename: str, formatter: Optional[str] = None):
        """Format Python file"""
        formatter = formatter or self.config['python_formatter']

        if formatter == 'black' and 'black' in self.available_formatters:
            self._run_command([
                'black',
                '--line-length', str(self.config['python_line_length']),
                filename
            ])

            # Also run isort if configured
            if self.config['use_isort'] and 'isort' in self.available_formatters:
                self._run_command(['isort', filename])

        elif formatter == 'autopep8' and 'autopep8' in self.available_formatters:
            self._run_command([
                'autopep8',
                '--in-place',
                '--max-line-length', str(self.config['python_line_length']),
                filename
            ])

        else:
            raise Exception(f"Python formatter '{formatter}' not available")

    def _format_javascript(self, filename: str):
        """Format JavaScript/TypeScript file"""
        if 'prettier' in self.available_formatters:
            self._run_command(['prettier', '--write', filename])
        else:
            raise Exception("prettier not available")

    def _format_go(self, filename: str):
        """Format Go file"""
        if 'gofmt' in self.available_formatters:
            self._run_command(['gofmt', '-w', filename])
        else:
            raise Exception("gofmt not available")

    def _format_rust(self, filename: str):
        """Format Rust file"""
        if 'rustfmt' in self.available_formatters:
            self._run_command(['rustfmt', filename])
        else:
            raise Exception("rustfmt not available")

    def _format_json(self, filename: str):
        """Format JSON file"""
        if 'jq' in self.available_formatters:
            # Use jq to format
            result = subprocess.run(
                ['jq', '.', filename],
                capture_output=True,
                text=True,
                check=True
            )
            with open(filename, 'w') as f:
                f.write(result.stdout)
        else:
            # Fallback to Python json module
            import json
            with open(filename, 'r') as f:
                data = json.load(f)
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

    def _lint_buffer(self, filename: str) -> List[str]:
        """
        Run linter on buffer

        Args:
            filename: File to lint

        Returns:
            List of lint results
        """
        language = self._detect_language(filename)
        results = []

        if language == 'python' and 'flake8' in self.available_formatters:
            try:
                output = self._run_command(['flake8', filename], check=False)
                if output:
                    results = output.splitlines()
            except Exception:
                pass

        return results

    def _run_command(self, cmd: List[str], check: bool = True) -> str:
        """
        Run external command

        Args:
            cmd: Command to run
            check: Whether to raise on non-zero exit

        Returns:
            Command output

        Raises:
            Exception: If command fails and check=True
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                timeout=30
            )
            return result.stdout

        except subprocess.CalledProcessError as e:
            raise Exception(f"Command failed: {e.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception("Command timed out")

        except FileNotFoundError:
            raise Exception(f"Command not found: {cmd[0]}")

    def _check_available_formatters(self) -> List[str]:
        """
        Check which formatters are available

        Returns:
            List of available formatter names
        """
        formatters_to_check = [
            'black', 'autopep8', 'isort',  # Python
            'prettier',                     # JS/TS
            'gofmt',                        # Go
            'rustfmt',                      # Rust
            'jq',                          # JSON
            'flake8', 'pylint',            # Python linters
        ]

        available = []
        for formatter in formatters_to_check:
            try:
                subprocess.run(
                    [formatter, '--version'],
                    capture_output=True,
                    timeout=5
                )
                available.append(formatter)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return available

    def _detect_language(self, filename: str) -> str:
        """
        Detect language from filename

        Args:
            filename: File path

        Returns:
            Language name
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.json': 'json',
        }

        ext = Path(filename).suffix
        return ext_map.get(ext, 'unknown')

    def get_config_schema(self) -> Dict:
        """Get configuration schema"""
        return {
            'auto_format_on_save': {
                'type': 'boolean',
                'default': False,
                'description': 'Automatically format buffer on save'
            },
            'python_formatter': {
                'type': 'string',
                'default': 'black',
                'description': 'Python formatter to use (black or autopep8)'
            },
            'python_line_length': {
                'type': 'integer',
                'default': 88,
                'description': 'Maximum line length for Python'
            },
            'use_isort': {
                'type': 'boolean',
                'default': True,
                'description': 'Use isort to sort Python imports'
            },
        }
