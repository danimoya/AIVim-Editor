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
    openai_model: str = "gpt-4.1-mini"
    anthropic_model: str = "claude-sonnet-5-5"
    timeout: float = 30.0
    auto_suggestions: bool = False
    nlp_live_mode: bool = False
    max_tokens: int = 2048
    temperature: float = 0.7
    stream_responses: bool = False
    show_thinking: bool = False
    cache_responses: bool = False
    retry_on_error: bool = True
    max_retries: int = 1
    local_model_path: str = ''
    local_model_sha256: str = ''
    local_memory_mb: int = 4096
    local_cpu_seconds: int = 60
    local_threads: int = 2
    local_context: int = 4096
    content_log_dir: str = '~/.local/state/aivim/content-logs'
    content_log_retention: int = 10
    
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
    swapfile: bool = False
    updatetime: int = 4000  # Milliseconds before swap file write
    undofile: bool = False
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
    
    SUPPORTED={
        'editor': {'tabstop','expandtab','shiftwidth','autoindent','number','relativenumber','cursorline','cursorcolumn','scrolloff'},
        'display': {'syntax'},
        'ai': {'default_model','openai_model','anthropic_model','timeout','nlp_live_mode','max_tokens','temperature','retry_on_error','max_retries','local_model_path','local_model_sha256','local_memory_mb','local_cpu_seconds','local_threads','local_context','content_log_dir','content_log_retention'},
        'file': {'auto_backup','backup_dir','encoding','fileformat','undolevels'},
        'search': {'ignorecase','smartcase','hlsearch','incsearch','wrapscan','gdefault'}
    }

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
        
    def _find_config_file(self, config_path=None):
        return Path(config_path).expanduser() if config_path else Path('~/.config/aivim/settings.json').expanduser()
    
    def load(self, path=None):
        import configparser
        target=Path(path).expanduser() if path else self.config_path
        self.loaded=False;self.legacy_credentials={}
        if not target.exists(): return False
        text=target.read_text(encoding='utf-8')
        if text.lstrip().startswith('['):
            legacy=configparser.ConfigParser();legacy.read_string(text)
            data={'schema_version':1,'ai':{}}
            for section,old,new in [('General','default_model','default_model'),('OpenAI','model','openai_model'),('Anthropic','model','anthropic_model'),('LocalLLM','model_path','local_model_path')]:
                if legacy.has_option(section,old): data['ai'][new]=legacy[section][old]
            for section,provider in [('OpenAI','openai'),('Anthropic','claude')]:
                if legacy.has_option(section,'api_key'):self.legacy_credentials[provider]=legacy[section]['api_key']
            for section,key,dest,kind in [('General','ai_timeout','timeout',int),('General','timeout','timeout',int),('LocalLLM','model_sha256','local_model_sha256',str)]:
                if legacy.has_option(section,key):data['ai'][dest]=kind(legacy[section][key])
            # Legacy credentials stay transient and are never serialized.
        else: data=json.loads(text)
        self.validate_config(data)
        for name,kind in [('editor',EditorSettings),('display',DisplaySettings),('ai',AISettings),('file',FileSettings),('search',SearchSettings)]:
            if name in data: setattr(self,name,kind.from_dict(data[name]))
        self.loaded=True;self._store_original_values();return True
    
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
            data={'schema_version':1,**self.get_all()}
            self.validate_config(data)
            import tempfile
            fd,temp=tempfile.mkstemp(dir=config_file.parent,prefix='.aivim-settings-')
            try:
                with os.fdopen(fd,'w') as f: json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
                os.replace(temp,config_file)
            finally:
                if os.path.exists(temp):os.unlink(temp)
            
            logging.info("Settings saved")
            return True
            
        except Exception as e:
            logging.error("settings operation failed")
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
                            if value.lower() not in ('true','1','yes','on','false','0','no','off'):raise ValueError('Invalid boolean')
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        else:
                            value = bool(value)
                    elif isinstance(current_value, int):
                        value = int(value)
                    elif isinstance(current_value, float):
                        value = float(value)
                    elif isinstance(current_value, str):
                        value = str(value)
                    
                    name=next(name for name in ('editor','display','ai','file','search') if getattr(self,name) is category)
                    self.validate_config({name:{option:value}})
                    setattr(category, option, value)
                    
                    # Auto-save if enabled
                    if self.auto_save:
                        self.save()
                    
                    return True
                except (ValueError, TypeError) as e:
                    logging.error("settings operation failed")
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
    
    def get_all(self):
        return {name:{key:getattr(getattr(self,name),key) for key in sorted(keys)} for name,keys in self.SUPPORTED.items()}
    
    def get_help(self):
        return ['Supported settings; unsupported options are rejected:']+[name+': '+', '.join(sorted(keys)) for name,keys in self.SUPPORTED.items()]
    
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
    @staticmethod
    def validate_config(data):
        if not isinstance(data,dict) or data.get('schema_version',1)!=1: raise ValueError('Expected settings schema_version 1')
        kinds={'editor':EditorSettings,'display':DisplaySettings,'ai':AISettings,'file':FileSettings,'search':SearchSettings}
        if set(data)-set(kinds)-{'schema_version'}: raise ValueError('Unknown settings category; credentials must be supplied separately')
        for category,values in data.items():
            if category=='schema_version': continue
            if not isinstance(values,dict): raise ValueError('Settings category must be an object')
            defaults=kinds[category]()
            for key,value in values.items():
                if key not in Settings.SUPPORTED[category]: raise ValueError('Unsupported setting: '+key)
                if key not in defaults.__dataclass_fields__: raise ValueError('Unknown setting: '+key)
                if isinstance(value,str) and '\0' in value:raise ValueError('Setting contains a null character')
                if key=='encoding':__import__('codecs').lookup(value)
                if key=='undolevels' and not 1<=value<=10000:raise ValueError('Invalid undo limit')
                expected=type(getattr(defaults,key))
                if expected is float and type(value) in (int,float): pass
                elif type(value) is not expected: raise ValueError('Invalid setting type: '+key)
                if key in {'stream_responses','cache_responses','auto_suggestions','swapfile','undofile','autowrite','autowriteall'} and value: raise ValueError('Unsupported setting: '+key)
                if key in {'tabstop','shiftwidth'} and not 1<=value<=32: raise ValueError('Invalid indentation width')
                if key=='timeout' and not .01<=value<=300: raise ValueError('Invalid timeout')
                if key=='default_model' and value not in {'openai','claude','local'}: raise ValueError('Unknown provider')
                if key=='fileformat' and value not in {'unix','dos','mac'}: raise ValueError('Unknown newline convention')
                if key=='max_retries' and not 0<=value<=3: raise ValueError('Invalid retry budget')
                if key=='temperature' and not 0<=value<=1: raise ValueError('Invalid temperature')
                if key=='max_tokens' and not 1<=value<=32768: raise ValueError('Invalid token budget')
                if key in {'local_memory_mb','local_cpu_seconds','local_threads','local_context','content_log_retention'} and value<=0: raise ValueError('Invalid resource limit')
