"""
Plugin manager for AIVim
"""
import os
import sys
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from .base import Plugin
from ..exceptions import PluginError, PluginLoadError, PluginNotFoundError

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manage AIVim plugins

    Handles plugin discovery, loading, initialization, and lifecycle.
    """

    def __init__(self, editor=None):
        """
        Initialize plugin manager

        Args:
            editor: Optional editor instance
        """
        self.editor = editor
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_paths: List[Path] = []
        self.enabled_plugins: set = set()

        # Default plugin directories
        self._add_default_paths()

    def _add_default_paths(self):
        """Add default plugin search paths"""
        default_paths = [
            Path.home() / ".aivim" / "plugins",
            Path.home() / ".config" / "aivim" / "plugins",
            Path(__file__).parent / "builtin",  # Built-in plugins
        ]

        for path in default_paths:
            if path.exists():
                self.add_plugin_path(path)

    def add_plugin_path(self, path: Path):
        """
        Add a directory to plugin search path

        Args:
            path: Directory path containing plugins
        """
        path = Path(path).resolve()
        if path not in self.plugin_paths:
            self.plugin_paths.append(path)
            logger.info(f"Added plugin path: {path}")

    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in search paths

        Returns:
            List of discovered plugin names
        """
        discovered = []

        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                continue

            for item in plugin_path.iterdir():
                if item.is_file() and item.suffix == ".py" and item.stem != "__init__":
                    discovered.append(item.stem)
                elif item.is_dir() and (item / "__init__.py").exists():
                    discovered.append(item.name)

        logger.info(f"Discovered {len(discovered)} plugins: {', '.join(discovered)}")
        return discovered

    def load_plugin(self, plugin_name: str) -> Plugin:
        """
        Load a plugin by name

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            Loaded plugin instance

        Raises:
            PluginLoadError: If plugin loading fails
            PluginNotFoundError: If plugin is not found
        """
        if plugin_name in self.plugins:
            logger.debug(f"Plugin {plugin_name} already loaded")
            return self.plugins[plugin_name]

        # Find plugin file
        plugin_file = self._find_plugin_file(plugin_name)
        if not plugin_file:
            raise PluginNotFoundError(plugin_name)

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            if spec is None or spec.loader is None:
                raise PluginLoadError(plugin_name, "Failed to load module spec")

            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)

            # Find Plugin subclass
            plugin_class = self._find_plugin_class(module, plugin_name)
            if not plugin_class:
                raise PluginLoadError(
                    plugin_name, "No Plugin subclass found in module"
                )

            # Instantiate plugin
            plugin = plugin_class()

            # Validate plugin
            if not isinstance(plugin, Plugin):
                raise PluginLoadError(
                    plugin_name, f"Plugin class must inherit from Plugin"
                )

            # Check dependencies
            self._check_dependencies(plugin)

            # Initialize plugin
            if self.editor:
                plugin.initialize(self.editor)

            # Store plugin
            self.plugins[plugin_name] = plugin
            self.enabled_plugins.add(plugin_name)

            logger.info(
                f"Loaded plugin: {plugin.get_name()} v{plugin.get_version()}"
            )
            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            raise PluginLoadError(plugin_name, str(e))

    def _find_plugin_file(self, plugin_name: str) -> Optional[Path]:
        """Find plugin file in search paths"""
        for plugin_path in self.plugin_paths:
            # Check for single file plugin
            plugin_file = plugin_path / f"{plugin_name}.py"
            if plugin_file.exists():
                return plugin_file

            # Check for directory plugin
            plugin_dir = plugin_path / plugin_name
            if plugin_dir.is_dir():
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    return init_file

        return None

    def _find_plugin_class(self, module, plugin_name: str):
        """Find Plugin subclass in module"""
        for item_name in dir(module):
            item = getattr(module, item_name)
            if (
                isinstance(item, type)
                and issubclass(item, Plugin)
                and item is not Plugin
            ):
                return item
        return None

    def _check_dependencies(self, plugin: Plugin):
        """Check and load plugin dependencies"""
        dependencies = plugin.get_dependencies()
        for dep in dependencies:
            if dep not in self.plugins:
                logger.info(f"Loading dependency: {dep}")
                self.load_plugin(dep)

    def unload_plugin(self, plugin_name: str):
        """
        Unload a plugin

        Args:
            plugin_name: Name of plugin to unload
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} not loaded")
            return

        plugin = self.plugins[plugin_name]

        # Call shutdown hook
        try:
            plugin.shutdown()
        except Exception as e:
            logger.error(f"Error during plugin shutdown: {e}")

        # Remove from registry
        del self.plugins[plugin_name]
        self.enabled_plugins.discard(plugin_name)

        logger.info(f"Unloaded plugin: {plugin_name}")

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a loaded plugin by name

        Args:
            plugin_name: Plugin name

        Returns:
            Plugin instance or None if not loaded
        """
        return self.plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """
        List all loaded plugins

        Returns:
            List of plugin names
        """
        return list(self.plugins.keys())

    def get_commands(self) -> Dict[str, Callable]:
        """
        Get all commands from loaded plugins

        Returns:
            Dictionary mapping command names to handler functions
        """
        commands = {}
        for plugin in self.plugins.values():
            plugin_commands = plugin.get_commands()
            for cmd_name, cmd_handler in plugin_commands.items():
                if cmd_name in commands:
                    logger.warning(
                        f"Command '{cmd_name}' from plugin '{plugin.get_name()}' "
                        f"conflicts with existing command"
                    )
                commands[cmd_name] = cmd_handler
        return commands

    def execute_command(self, command: str, args: str = "") -> bool:
        """
        Execute a plugin command

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was found and executed
        """
        commands = self.get_commands()
        if command in commands:
            try:
                commands[command](args)
                return True
            except Exception as e:
                logger.error(f"Error executing plugin command '{command}': {e}")
                raise
        return False

    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """
        Trigger a hook on all loaded plugins

        Args:
            hook_name: Name of the hook method
            *args: Positional arguments for the hook
            **kwargs: Keyword arguments for the hook
        """
        for plugin_name, plugin in self.plugins.items():
            if plugin_name not in self.enabled_plugins:
                continue

            try:
                hook_method = getattr(plugin, hook_name, None)
                if hook_method and callable(hook_method):
                    hook_method(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in plugin '{plugin_name}' hook '{hook_name}': {e}"
                )

    def reload_plugin(self, plugin_name: str) -> Plugin:
        """
        Reload a plugin

        Args:
            plugin_name: Name of plugin to reload

        Returns:
            Reloaded plugin instance
        """
        if plugin_name in self.plugins:
            self.unload_plugin(plugin_name)

        return self.load_plugin(plugin_name)

    def get_plugin_status(self, plugin_name: Optional[str] = None) -> Dict:
        """
        Get status information for plugin(s)

        Args:
            plugin_name: Optional specific plugin name

        Returns:
            Dictionary with status information
        """
        if plugin_name:
            plugin = self.get_plugin(plugin_name)
            if plugin:
                return plugin.get_status()
            return {}

        return {
            name: plugin.get_status() for name, plugin in self.plugins.items()
        }
