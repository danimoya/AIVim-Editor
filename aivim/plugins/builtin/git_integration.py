"""
Git integration plugin for AIVim

Provides Git commands and status information directly in the editor.
"""
import os
import subprocess
import logging
from typing import Dict, Callable, Optional

from ..base import Plugin

logger = logging.getLogger(__name__)


class GitIntegrationPlugin(Plugin):
    """
    Git integration plugin

    Features:
    - :git-status - Show git status
    - :git-diff - Show git diff in new tab
    - :git-add - Stage current file
    - :git-commit - Commit with message
    - Auto-status on buffer save (optional)
    """

    def get_name(self) -> str:
        """Get plugin name"""
        return "git-integration"

    def get_version(self) -> str:
        """Get plugin version"""
        return "1.0.0"

    def get_description(self) -> str:
        """Get plugin description"""
        return "Git integration for AIVim with status, diff, and commit commands"

    def get_author(self) -> str:
        """Get plugin author"""
        return "AIVim Team"

    def initialize(self, editor):
        """
        Initialize plugin

        Args:
            editor: Editor instance
        """
        self.editor = editor
        self.config = {
            'auto_status': True,  # Show status on save
            'auto_add': False,    # Auto-add on save
        }

        logger.info("Git integration plugin initialized")

    def get_commands(self) -> Dict[str, Callable]:
        """
        Get plugin commands

        Returns:
            Dictionary of command names to handlers
        """
        return {
            "git-status": self.cmd_git_status,
            "git-diff": self.cmd_git_diff,
            "git-add": self.cmd_git_add,
            "git-commit": self.cmd_git_commit,
            "git-log": self.cmd_git_log,
        }

    def configure(self, config: Dict):
        """
        Configure plugin

        Args:
            config: Configuration dictionary
        """
        if 'auto_status' in config:
            self.config['auto_status'] = config['auto_status']
        if 'auto_add' in config:
            self.config['auto_add'] = config['auto_add']

        logger.info(f"Git plugin configured: {self.config}")

    def on_buffer_save(self, buffer, filename: str):
        """
        Hook called when buffer is saved

        Args:
            buffer: Buffer instance
            filename: Saved filename
        """
        if not filename:
            return

        # Auto-add if configured
        if self.config.get('auto_add'):
            try:
                self._run_git_command(['add', filename])
                logger.debug(f"Auto-added {filename} to git")
            except Exception as e:
                logger.error(f"Failed to auto-add {filename}: {e}")

        # Show status if configured
        if self.config.get('auto_status'):
            try:
                status = self._get_file_status(filename)
                if status:
                    self.editor.status_message = f"Git: {status}"
            except Exception:
                pass

    def cmd_git_status(self, args: str):
        """
        Show git status

        Args:
            args: Command arguments (unused)
        """
        try:
            output = self._run_git_command(['status', '--short'])

            if not output:
                self.editor.status_message = "Git: Working tree clean"
                return

            # Create new tab with status
            status_text = f"Git Status\n{'='*50}\n\n{output}"
            self.editor.create_tab("Git Status", temporary=True)
            self.editor.buffer.set_lines(status_text.splitlines())
            self.editor.mode = "NORMAL"

            logger.debug("Git status displayed")

        except Exception as e:
            self.editor.status_message = f"Git error: {e}"
            logger.error(f"Git status failed: {e}")

    def cmd_git_diff(self, args: str):
        """
        Show git diff

        Args:
            args: Optional file path or diff options
        """
        try:
            # Build diff command
            cmd = ['diff']
            if args:
                cmd.extend(args.split())

            output = self._run_git_command(cmd)

            if not output:
                self.editor.status_message = "Git: No changes to diff"
                return

            # Create new tab with diff
            self.editor.create_tab("Git Diff", temporary=True)
            self.editor.buffer.set_lines(output.splitlines())
            self.editor.mode = "NORMAL"

            logger.debug("Git diff displayed")

        except Exception as e:
            self.editor.status_message = f"Git error: {e}"
            logger.error(f"Git diff failed: {e}")

    def cmd_git_add(self, args: str):
        """
        Stage file(s)

        Args:
            args: Files to add (default: current file)
        """
        try:
            if args:
                files = args.split()
            else:
                # Add current file
                if not self.editor.filename:
                    self.editor.status_message = "No file to add"
                    return
                files = [self.editor.filename]

            # Add files
            for filename in files:
                self._run_git_command(['add', filename])

            self.editor.status_message = f"Git: Added {', '.join(files)}"
            logger.debug(f"Added files to git: {files}")

        except Exception as e:
            self.editor.status_message = f"Git error: {e}"
            logger.error(f"Git add failed: {e}")

    def cmd_git_commit(self, args: str):
        """
        Commit staged changes

        Args:
            args: Commit message
        """
        if not args:
            self.editor.status_message = "Git: Commit message required"
            return

        try:
            output = self._run_git_command(['commit', '-m', args])
            self.editor.status_message = f"Git: {output.splitlines()[0]}"
            logger.info(f"Git commit: {args}")

        except Exception as e:
            self.editor.status_message = f"Git error: {e}"
            logger.error(f"Git commit failed: {e}")

    def cmd_git_log(self, args: str):
        """
        Show git log

        Args:
            args: Log options (e.g., '-10' for last 10 commits)
        """
        try:
            cmd = ['log', '--oneline', '--decorate']
            if args:
                cmd.extend(args.split())
            else:
                cmd.append('-20')  # Default: last 20 commits

            output = self._run_git_command(cmd)

            if not output:
                self.editor.status_message = "Git: No commits"
                return

            # Create new tab with log
            log_text = f"Git Log\n{'='*50}\n\n{output}"
            self.editor.create_tab("Git Log", temporary=True)
            self.editor.buffer.set_lines(log_text.splitlines())
            self.editor.mode = "NORMAL"

            logger.debug("Git log displayed")

        except Exception as e:
            self.editor.status_message = f"Git error: {e}"
            logger.error(f"Git log failed: {e}")

    def _run_git_command(self, args: list) -> str:
        """
        Run git command

        Args:
            args: Git command arguments

        Returns:
            Command output

        Raises:
            Exception: If git command fails
        """
        try:
            result = subprocess.run(
                ['git'] + args,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            raise Exception(f"Git command failed: {e.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception("Git command timed out")

        except FileNotFoundError:
            raise Exception("Git not found - is it installed?")

    def _get_file_status(self, filename: str) -> Optional[str]:
        """
        Get git status of a file

        Args:
            filename: File path

        Returns:
            Status string or None
        """
        try:
            output = self._run_git_command(['status', '--short', filename])
            if output:
                # Parse status (e.g., "M  file.txt" -> "Modified")
                status_code = output[:2].strip()
                status_map = {
                    'M': 'Modified',
                    'A': 'Added',
                    'D': 'Deleted',
                    'R': 'Renamed',
                    'C': 'Copied',
                    '??': 'Untracked',
                }
                return status_map.get(status_code, status_code)
            return None

        except Exception:
            return None

    def get_config_schema(self) -> Dict:
        """
        Get configuration schema

        Returns:
            Configuration schema dictionary
        """
        return {
            'auto_status': {
                'type': 'boolean',
                'default': True,
                'description': 'Show git status after saving file'
            },
            'auto_add': {
                'type': 'boolean',
                'default': False,
                'description': 'Automatically stage file after saving'
            },
        }
