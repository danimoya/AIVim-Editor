"""
Settings management system for AIVim
"""
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, field, asdict


@dataclass
class EditorSettings:
    """Editor-related settings"""
    tabstop: int = 4
    expandtab: bool = True
    shiftwidth: int = 4
    autoindent: bool = True
    wrap: bool = True
    number: bool = True
    relativenumber: bool = False
    showmatch: bool = True
    matchtime: int = 2
    scrolloff: int = 3
    cursorline: bool = True
    cursorcolumn: bool = False
    colorcolumn: int = 0  # 0 means disabled
    textwidth: int = 0  # 0 means no automatic wrapping
    autoread: bool = True
    backspace: str = "indent,eol,start"
    clipboard: str = "unnamedplus"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditorSettings':
        """Create from dictionary"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class DisplaySettings:
    """Display-related settings"""
    theme: str = "default"
    syntax: bool = True
    statusline: str = "[{mode}] {filename} {modified} L{line}:{col} {percent}%"
    laststatus: int = 2  # 0=never, 1=only with multiple windows, 2=always
    ruler: bool = True
    showcmd: bool = True
    showmode: bool = True
    wildmenu: bool = True
    wildmode: str = "list:longest,full"
    title: bool = True
    titlestring: str = "AIVim - {filename}"
    list: bool = False  # Show special characters
    listchars: str = "tab:→ ,trail:·,extends:›,precedes:‹"
    fillchars: str = "vert:│,fold:·"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DisplaySettings':
        """Create from dictionary"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class AISettings:
    """AI-related settings"""
    default_model: str = "openai"
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    timeout: int = 30
    auto_suggestions: bool = True
    nlp_live_mode: bool = False
    max_tokens: int = 2048
    temperature: float = 0.7
    stream_responses: bool = True
    show_thinking: bool = False
    cache_responses: bool = True
    retry_on_error: bool = True
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AISettings':
        """Create from dictionary"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class FileSettings:
    """File operation settings"""
    auto_backup: bool = True
    backup_dir: str = "~/.aivim/backups"
    encoding: str = "utf-8"
    fileformat: str = "unix"  # unix, dos, mac
    bomb: bool = False  # Byte order mark
    autowrite: bool = False
    autowriteall: bool = False
    backup: bool = False  # Keep backup after successful write
    writebackup: bool = True  # Make backup before overwriting
    swapfile: bool = True
    updatetime: int = 4000  # Milliseconds before swap file write
    undofile: bool = True
    undodir: str = "~/.aivim/undo"
    undolevels: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileSettings':
        """Create from dictionary"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass  
class SearchSettings:
    """Search-related settings"""
    ignorecase: bool = True
    smartcase: bool = True
    hlsearch: bool = True
    incsearch: bool = True
    wrapscan: bool = True
    magic: bool = True
    regexpengine: int = 0  # 0=automatic, 1=old, 2=NFA
    gdefault: bool = False  # Global flag default for substitutions
    inccommand: str = "nosplit"  # Live preview for substitutions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchSettings':
        """Create from dictionary"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class Settings:
    """Main settings manager for AIVim"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings manager
        
        Args:
            config_path: Optional path to config file. If not provided,
                        will look for ~/.aivimrc or ~/.config/aivim/settings.json
        """
        # Initialize setting categories
        self.editor = EditorSettings()
        self.display = DisplaySettings()
        self.ai = AISettings()
        self.file = FileSettings()
        self.search = SearchSettings()
        
        # Config file management
        self.config_path = self._find_config_file(config_path)
        self.auto_save = False
        self._original_values = {}  # Store original values for reset
        
        # Option aliases for vim compatibility
        self._aliases = {
            'ts': 'tabstop',
            'et': 'expandtab',
            'sw': 'shiftwidth',
            'ai': 'autoindent',
            'nu': 'number',
            'rnu': 'relativenumber',
            'ic': 'ignorecase',
            'sc': 'smartcase',
            'hls': 'hlsearch',
            'is': 'incsearch',
            'ws': 'wrapscan',
            'syn': 'syntax',
            'so': 'scrolloff',
            'cul': 'cursorline',
            'cuc': 'cursorcolumn',
            'cc': 'colorcolumn',
            'tw': 'textwidth',
            'ar': 'autoread',
            'bs': 'backspace',
            'cb': 'clipboard',
            'ls': 'laststatus',
            'smd': 'showmode',
            'sc': 'showcmd',
            'wmnu': 'wildmenu',
            'wm': 'wildmode',
            'enc': 'encoding',
            'ff': 'fileformat',
            'aw': 'autowrite',
            'awa': 'autowriteall',
            'bk': 'backup',
            'wb': 'writebackup',
            'swf': 'swapfile',
            'ut': 'updatetime',
            'udf': 'undofile',
            'ud': 'undodir',
            'ul': 'undolevels',
            'gd': 'gdefault',
            're': 'regexpengine',
        }
        
        # Load configuration
        self.load()
        
    def _find_config_file(self, config_path: Optional[str] = None) -> Path:
        """Find the configuration file
        
        Args:
            config_path: Optional explicit config path
            
        Returns:
            Path to the config file
        """
        if config_path:
            return Path(config_path).expanduser()
        
        # Check common config locations
        config_locations = [
            Path.home() / '.aivimrc',
            Path.home() / '.config' / 'aivim' / 'settings.json',
            Path.home() / '.aivim' / 'config.json',
        ]
        
        for path in config_locations:
            if path.exists():
                logging.info(f"Found config file at: {path}")
                return path
        
        # Default to ~/.config/aivim/settings.json
        default_path = Path.home() / '.config' / 'aivim' / 'settings.json'
        logging.info(f"No config file found, using default: {default_path}")
        return default_path
    
    def load(self, path: Optional[str] = None) -> bool:
        """Load settings from file
        
        Args:
            path: Optional path to load from
            
        Returns:
            True if successful, False otherwise
        """
        config_file = Path(path).expanduser() if path else self.config_path
        
        if not config_file.exists():
            logging.info(f"Config file not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            # Load each category
            if 'editor' in data:
                self.editor = EditorSettings.from_dict(data['editor'])
            if 'display' in data:
                self.display = DisplaySettings.from_dict(data['display'])
            if 'ai' in data:
                self.ai = AISettings.from_dict(data['ai'])
            if 'file' in data:
                self.file = FileSettings.from_dict(data['file'])
            if 'search' in data:
                self.search = SearchSettings.from_dict(data['search'])
            
            # Store original values for reset
            self._store_original_values()
            
            logging.info(f"Settings loaded from: {config_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            return False
    
    def save(self, path: Optional[str] = None) -> bool:
        """Save settings to file
        
        Args:
            path: Optional path to save to
            
        Returns:
            True if successful, False otherwise
        """
        config_file = Path(path).expanduser() if path else self.config_path
        
        # Create directory if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                'editor': self.editor.to_dict(),
                'display': self.display.to_dict(),
                'ai': self.ai.to_dict(),
                'file': self.file.to_dict(),
                'search': self.search.to_dict(),
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Settings saved to: {config_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            return False
    
    def _store_original_values(self):
        """Store original values for reset functionality"""
        self._original_values = {
            'editor': self.editor.to_dict(),
            'display': self.display.to_dict(),
            'ai': self.ai.to_dict(),
            'file': self.file.to_dict(),
            'search': self.search.to_dict(),
        }
    
    def reset(self):
        """Reset settings to original values"""
        if self._original_values:
            self.editor = EditorSettings.from_dict(self._original_values.get('editor', {}))
            self.display = DisplaySettings.from_dict(self._original_values.get('display', {}))
            self.ai = AISettings.from_dict(self._original_values.get('ai', {}))
            self.file = FileSettings.from_dict(self._original_values.get('file', {}))
            self.search = SearchSettings.from_dict(self._original_values.get('search', {}))
        else:
            # Reset to defaults
            self.editor = EditorSettings()
            self.display = DisplaySettings()
            self.ai = AISettings()
            self.file = FileSettings()
            self.search = SearchSettings()
    
    def get(self, option: str) -> Any:
        """Get the value of a setting
        
        Args:
            option: Setting name (can be alias or full name)
            
        Returns:
            The setting value, or None if not found
        """
        # Resolve alias
        option = self._aliases.get(option, option)
        
        # Search in all categories
        for category in [self.editor, self.display, self.ai, self.file, self.search]:
            if hasattr(category, option):
                return getattr(category, option)
        
        return None
    
    def set(self, option: str, value: Any) -> bool:
        """Set the value of a setting
        
        Args:
            option: Setting name (can be alias or full name)
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        # Resolve alias
        option = self._aliases.get(option, option)
        
        # Find and update the setting
        for category in [self.editor, self.display, self.ai, self.file, self.search]:
            if hasattr(category, option):
                # Type conversion based on current type
                current_value = getattr(category, option)
                try:
                    if isinstance(current_value, bool):
                        # Handle boolean conversions
                        if isinstance(value, str):
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        else:
                            value = bool(value)
                    elif isinstance(current_value, int):
                        value = int(value)
                    elif isinstance(current_value, float):
                        value = float(value)
                    elif isinstance(current_value, str):
                        value = str(value)
                    
                    setattr(category, option, value)
                    
                    # Auto-save if enabled
                    if self.auto_save:
                        self.save()
                    
                    return True
                except (ValueError, TypeError) as e:
                    logging.error(f"Error setting {option}: {e}")
                    return False
        
        return False
    
    def toggle(self, option: str) -> bool:
        """Toggle a boolean setting
        
        Args:
            option: Setting name
            
        Returns:
            True if successful, False otherwise
        """
        current = self.get(option)
        if isinstance(current, bool):
            return self.set(option, not current)
        return False
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all settings as a dictionary
        
        Returns:
            Dictionary with all settings organized by category
        """
        return {
            'editor': self.editor.to_dict(),
            'display': self.display.to_dict(),
            'ai': self.ai.to_dict(),
            'file': self.file.to_dict(),
            'search': self.search.to_dict(),
        }
    
    def get_help(self) -> List[str]:
        """Get help text for all settings
        
        Returns:
            List of help lines
        """
        help_lines = [
            "AIVim Settings Help",
            "==================",
            "",
            "Usage:",
            "  :set option          - Show current value",
            "  :set option=value    - Set value",
            "  :set option!         - Toggle boolean option",
            "  :set nooption        - Turn off boolean option",
            "  :set all             - Show all settings",
            "  :set?                - Show this help",
            "",
            "Editor Settings:",
            "  tabstop (ts)         - Number of spaces for tab character",
            "  expandtab (et)       - Use spaces instead of tabs",
            "  shiftwidth (sw)      - Number of spaces for indent",
            "  autoindent (ai)      - Copy indent from current line",
            "  wrap                 - Wrap long lines",
            "  number (nu)          - Show line numbers",
            "  relativenumber (rnu) - Show relative line numbers",
            "  cursorline (cul)     - Highlight current line",
            "  scrolloff (so)       - Lines to keep above/below cursor",
            "",
            "Display Settings:",
            "  theme                - Color theme",
            "  syntax (syn)         - Enable syntax highlighting",
            "  statusline           - Status line format",
            "  showmode (smd)       - Show current mode",
            "  showcmd (sc)         - Show partial command",
            "  ruler                - Show cursor position",
            "",
            "AI Settings:",
            "  default_model        - Default AI model to use",
            "  timeout              - AI request timeout in seconds",
            "  auto_suggestions     - Enable automatic AI suggestions",
            "  nlp_live_mode        - Enable NLP live mode by default",
            "",
            "File Settings:",
            "  auto_backup          - Create backups automatically",
            "  backup_dir           - Directory for backup files",
            "  encoding (enc)       - File encoding",
            "  fileformat (ff)      - Line ending format (unix/dos/mac)",
            "  undolevels (ul)      - Number of undo levels",
            "",
            "Search Settings:",
            "  ignorecase (ic)      - Case insensitive search",
            "  smartcase (sc)       - Override ignorecase if uppercase used",
            "  hlsearch (hls)       - Highlight search matches",
            "  incsearch (is)       - Show matches while typing",
            "  wrapscan (ws)        - Wrap search at end of file",
        ]
        
        return help_lines
    
    def export_config(self, path: str) -> bool:
        """Export current settings to a file
        
        Args:
            path: Path to export to
            
        Returns:
            True if successful, False otherwise
        """
        return self.save(path)
    
    def import_config(self, path: str) -> bool:
        """Import settings from a file
        
        Args:
            path: Path to import from
            
        Returns:
            True if successful, False otherwise
        """
        return self.load(path)