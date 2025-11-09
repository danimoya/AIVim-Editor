"""
Plugin system for AIVim
"""
from .base import Plugin
from .manager import PluginManager

__all__ = ["Plugin", "PluginManager"]
