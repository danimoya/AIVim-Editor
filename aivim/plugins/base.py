"""
Base plugin class for AIVim
"""
from abc import ABC, abstractmethod
from typing import Dict, Callable, Optional, Any, List


class Plugin(ABC):
    """
    Base class for AIVim plugins

    Plugins can extend AIVim functionality by adding custom commands,
    keybindings, and integrations.

    Example:
        class MyPlugin(Plugin):
            def get_name(self) -> str:
                return "my-plugin"

            def get_version(self) -> str:
                return "1.0.0"

            def initialize(self, editor):
                self.editor = editor
                # Setup plugin

            def get_commands(self) -> Dict[str, Callable]:
                return {
                    "myplugin": self.my_command
                }

            def my_command(self, args: str):
                # Command implementation
                self.editor.status_message = "My plugin executed!"
    """

    @abstractmethod
    def get_name(self) -> str:
        """
        Get plugin name

        Returns:
            Plugin name (lowercase, hyphenated)
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """
        Get plugin version

        Returns:
            Version string (e.g., "1.0.0")
        """
        pass

    @abstractmethod
    def initialize(self, editor):
        """
        Initialize plugin with editor instance

        Args:
            editor: Editor instance
        """
        pass

    def get_description(self) -> str:
        """
        Get plugin description

        Returns:
            Human-readable description
        """
        return ""

    def get_author(self) -> str:
        """
        Get plugin author

        Returns:
            Author name/email
        """
        return "Unknown"

    def get_commands(self) -> Dict[str, Callable]:
        """
        Get plugin commands

        Returns:
            Dictionary mapping command names to handler functions
        """
        return {}

    def get_keybindings(self) -> Dict[str, Callable]:
        """
        Get plugin keybindings

        Returns:
            Dictionary mapping key sequences to handler functions
        """
        return {}

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get plugin configuration schema

        Returns:
            Dictionary describing configuration options
        """
        return {}

    def configure(self, config: Dict[str, Any]):
        """
        Configure plugin with user settings

        Args:
            config: Configuration dictionary
        """
        pass

    def on_buffer_open(self, buffer, filename: Optional[str]):
        """
        Hook called when a buffer is opened

        Args:
            buffer: Buffer instance
            filename: Optional filename
        """
        pass

    def on_buffer_close(self, buffer, filename: Optional[str]):
        """
        Hook called when a buffer is closed

        Args:
            buffer: Buffer instance
            filename: Optional filename
        """
        pass

    def on_buffer_save(self, buffer, filename: str):
        """
        Hook called when a buffer is saved

        Args:
            buffer: Buffer instance
            filename: Filename being saved to
        """
        pass

    def on_mode_change(self, old_mode: str, new_mode: str):
        """
        Hook called when editor mode changes

        Args:
            old_mode: Previous mode
            new_mode: New mode
        """
        pass

    def on_cursor_move(self, old_pos: tuple, new_pos: tuple):
        """
        Hook called when cursor moves

        Args:
            old_pos: Previous (line, column) position
            new_pos: New (line, column) position
        """
        pass

    def shutdown(self):
        """
        Cleanup when plugin is unloaded

        Override this to perform cleanup tasks
        """
        pass

    def get_dependencies(self) -> List[str]:
        """
        Get list of required plugin dependencies

        Returns:
            List of plugin names this plugin depends on
        """
        return []

    def is_compatible(self, aivim_version: str) -> bool:
        """
        Check if plugin is compatible with AIVim version

        Args:
            aivim_version: AIVim version string

        Returns:
            True if compatible
        """
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get plugin status information

        Returns:
            Dictionary with status information
        """
        return {
            "name": self.get_name(),
            "version": self.get_version(),
            "enabled": True,
        }
