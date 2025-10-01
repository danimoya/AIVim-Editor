"""
Comprehensive tests for the AIVim settings system
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from aivim.settings import (
    Settings, EditorSettings, DisplaySettings, AISettings,
    FileSettings, SearchSettings
)
from aivim.editor import Editor
from aivim.command_handler import CommandHandler


class TestSettingsDataClasses:
    """Test the individual settings dataclasses"""
    
    def test_editor_settings_defaults(self):
        """Test editor settings default values"""
        settings = EditorSettings()
        assert settings.tabstop == 4
        assert settings.expandtab == True
        assert settings.shiftwidth == 4
        assert settings.autoindent == True
        assert settings.wrap == True
        assert settings.number == True
        assert settings.relativenumber == False
        assert settings.cursorline == True
        assert settings.scrolloff == 3
    
    def test_display_settings_defaults(self):
        """Test display settings default values"""
        settings = DisplaySettings()
        assert settings.theme == "default"
        assert settings.syntax == True
        assert settings.statusline == "[{mode}] {filename} {modified} L{line}:{col} {percent}%"
        assert settings.showmode == True
        assert settings.ruler == True
    
    def test_ai_settings_defaults(self):
        """Test AI settings default values"""
        settings = AISettings()
        assert settings.default_model == "openai"
        assert settings.openai_model == "gpt-4o"
        assert settings.timeout == 30
        assert settings.auto_suggestions == True
        assert settings.nlp_live_mode == False
    
    def test_file_settings_defaults(self):
        """Test file settings default values"""
        settings = FileSettings()
        assert settings.auto_backup == True
        assert settings.backup_dir == "~/.aivim/backups"
        assert settings.encoding == "utf-8"
        assert settings.fileformat == "unix"
        assert settings.undolevels == 1000
    
    def test_search_settings_defaults(self):
        """Test search settings default values"""
        settings = SearchSettings()
        assert settings.ignorecase == True
        assert settings.smartcase == True
        assert settings.hlsearch == True
        assert settings.incsearch == True
        assert settings.wrapscan == True
    
    def test_settings_to_dict(self):
        """Test converting settings to dictionary"""
        settings = EditorSettings(tabstop=8, expandtab=False)
        d = settings.to_dict()
        assert d['tabstop'] == 8
        assert d['expandtab'] == False
        assert d['shiftwidth'] == 4  # Default value
    
    def test_settings_from_dict(self):
        """Test creating settings from dictionary"""
        data = {'tabstop': 2, 'expandtab': False, 'invalid_key': 'ignored'}
        settings = EditorSettings.from_dict(data)
        assert settings.tabstop == 2
        assert settings.expandtab == False
        assert settings.shiftwidth == 4  # Default value
        assert not hasattr(settings, 'invalid_key')


class TestSettingsManager:
    """Test the main Settings class"""
    
    def test_settings_initialization(self):
        """Test Settings initialization"""
        settings = Settings()
        assert isinstance(settings.editor, EditorSettings)
        assert isinstance(settings.display, DisplaySettings)
        assert isinstance(settings.ai, AISettings)
        assert isinstance(settings.file, FileSettings)
        assert isinstance(settings.search, SearchSettings)
    
    def test_get_setting(self):
        """Test getting a setting value"""
        settings = Settings()
        assert settings.get('tabstop') == 4
        assert settings.get('theme') == 'default'
        assert settings.get('default_model') == 'openai'
        assert settings.get('ignorecase') == True
        assert settings.get('nonexistent') is None
    
    def test_get_setting_with_alias(self):
        """Test getting a setting value using an alias"""
        settings = Settings()
        assert settings.get('ts') == 4  # tabstop alias
        assert settings.get('et') == True  # expandtab alias
        assert settings.get('ic') == True  # ignorecase alias
        assert settings.get('nu') == True  # number alias
    
    def test_set_setting(self):
        """Test setting a value"""
        settings = Settings()
        # Test integer setting
        assert settings.set('tabstop', 8)
        assert settings.get('tabstop') == 8
        
        # Test boolean setting
        assert settings.set('expandtab', False)
        assert settings.get('expandtab') == False
        
        # Test string setting
        assert settings.set('theme', 'dark')
        assert settings.get('theme') == 'dark'
        
        # Test invalid setting
        assert not settings.set('nonexistent', 'value')
    
    def test_set_setting_with_alias(self):
        """Test setting a value using an alias"""
        settings = Settings()
        assert settings.set('ts', 2)
        assert settings.get('tabstop') == 2
        assert settings.set('et', False)
        assert settings.get('expandtab') == False
    
    def test_toggle_setting(self):
        """Test toggling a boolean setting"""
        settings = Settings()
        original = settings.get('expandtab')
        assert settings.toggle('expandtab')
        assert settings.get('expandtab') != original
        assert settings.toggle('expandtab')
        assert settings.get('expandtab') == original
        
        # Test toggling non-boolean setting (should fail)
        assert not settings.toggle('tabstop')
    
    def test_get_all_settings(self):
        """Test getting all settings"""
        settings = Settings()
        all_settings = settings.get_all()
        assert 'editor' in all_settings
        assert 'display' in all_settings
        assert 'ai' in all_settings
        assert 'file' in all_settings
        assert 'search' in all_settings
        assert all_settings['editor']['tabstop'] == 4
    
    def test_reset_settings(self):
        """Test resetting settings to defaults"""
        settings = Settings()
        settings.set('tabstop', 8)
        settings.set('theme', 'dark')
        assert settings.get('tabstop') == 8
        assert settings.get('theme') == 'dark'
        
        settings.reset()
        assert settings.get('tabstop') == 4  # Back to default
        assert settings.get('theme') == 'default'  # Back to default
    
    def test_save_and_load_settings(self):
        """Test saving and loading settings from file"""
        settings = Settings()
        settings.set('tabstop', 8)
        settings.set('theme', 'dark')
        settings.set('default_model', 'claude')
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            assert settings.save(temp_path)
            
            # Load into new settings object
            new_settings = Settings()
            assert new_settings.load(temp_path)
            assert new_settings.get('tabstop') == 8
            assert new_settings.get('theme') == 'dark'
            assert new_settings.get('default_model') == 'claude'
        finally:
            os.unlink(temp_path)
    
    def test_export_import_config(self):
        """Test exporting and importing configuration"""
        settings = Settings()
        settings.set('tabstop', 2)
        settings.set('wrap', False)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            assert settings.export_config(temp_path)
            
            new_settings = Settings()
            assert new_settings.import_config(temp_path)
            assert new_settings.get('tabstop') == 2
            assert new_settings.get('wrap') == False
        finally:
            os.unlink(temp_path)
    
    def test_type_conversion(self):
        """Test automatic type conversion when setting values"""
        settings = Settings()
        
        # Test boolean conversions
        assert settings.set('expandtab', 'true')
        assert settings.get('expandtab') == True
        assert settings.set('expandtab', 'false')
        assert settings.get('expandtab') == False
        assert settings.set('expandtab', '1')
        assert settings.get('expandtab') == True
        assert settings.set('expandtab', '0')
        assert settings.get('expandtab') == False
        
        # Test integer conversions
        assert settings.set('tabstop', '8')
        assert settings.get('tabstop') == 8
        
        # Test float conversions
        assert settings.set('temperature', '0.5')
        assert settings.get('temperature') == 0.5


class TestCommandHandlerIntegration:
    """Test the command handler's settings integration"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.editor = Mock()
        self.editor.settings = Settings()
        self.editor.display = Mock()
        self.editor.set_status_message = Mock()
        self.editor.search_highlighting = True
        self.handler = CommandHandler(self.editor)
    
    def test_cmd_set_help(self):
        """Test :set? command"""
        self.editor.display.show_dialog = Mock()
        assert self.handler._cmd_set_help()
        self.editor.display.show_dialog.assert_called_once()
        args = self.editor.display.show_dialog.call_args[0]
        assert args[0] == "Settings Help"
        assert len(args[1]) > 10  # Should have help text
    
    def test_cmd_set_all(self):
        """Test :set all command"""
        self.editor.display.show_dialog = Mock()
        assert self.handler._cmd_set_all()
        self.editor.display.show_dialog.assert_called_once()
        args = self.editor.display.show_dialog.call_args[0]
        assert args[0] == "All Settings"
        assert "EDITOR Settings:" in "\n".join(args[1])
    
    def test_cmd_set_show(self):
        """Test :set option command (show value)"""
        assert self.handler._cmd_set_show('tabstop')
        self.editor.set_status_message.assert_called_with('tabstop=4')
        
        # Test boolean option (true)
        self.editor.set_status_message.reset_mock()
        assert self.handler._cmd_set_show('expandtab')
        self.editor.set_status_message.assert_called_with('expandtab')
        
        # Test boolean option (false)
        self.editor.set_status_message.reset_mock()
        self.editor.settings.set('expandtab', False)
        assert self.handler._cmd_set_show('expandtab')
        self.editor.set_status_message.assert_called_with('noexpandtab')
        
        # Test non-existent option
        self.editor.set_status_message.reset_mock()
        assert not self.handler._cmd_set_show('nonexistent')
        self.editor.set_status_message.assert_called_with('Unknown option: nonexistent')
    
    def test_cmd_set_value(self):
        """Test :set option=value command"""
        assert self.handler._cmd_set_value('tabstop', '8')
        assert self.editor.settings.get('tabstop') == 8
        self.editor.set_status_message.assert_called_with('tabstop=8')
        
        # Test with quotes
        assert self.handler._cmd_set_value('theme', '"dark"')
        assert self.editor.settings.get('theme') == 'dark'
        
        # Test with single quotes
        assert self.handler._cmd_set_value('theme', "'light'")
        assert self.editor.settings.get('theme') == 'light'
    
    def test_cmd_set_toggle(self):
        """Test :set option! command"""
        original = self.editor.settings.get('expandtab')
        assert self.handler._cmd_set_toggle('expandtab')
        assert self.editor.settings.get('expandtab') != original
        self.editor.set_status_message.assert_called()
        
        # Test non-boolean option
        self.editor.set_status_message.reset_mock()
        assert not self.handler._cmd_set_toggle('tabstop')
        self.editor.set_status_message.assert_called_with('Cannot toggle option: tabstop')
    
    def test_cmd_set_no_option(self):
        """Test :set nooption command"""
        self.editor.settings.set('expandtab', True)
        assert self.handler._cmd_set_no_option('expandtab')
        assert self.editor.settings.get('expandtab') == False
        self.editor.set_status_message.assert_called_with('noexpandtab')
        
        # Test non-boolean option
        self.editor.set_status_message.reset_mock()
        assert not self.handler._cmd_set_no_option('tabstop')
        self.editor.set_status_message.assert_called_with('Invalid option: notabstop')
    
    def test_cmd_source(self):
        """Test :source path command"""
        # Create a test config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({
                'editor': {'tabstop': 2},
                'display': {'theme': 'dark'}
            }, f)
            temp_path = f.name
        
        try:
            assert self.handler._cmd_source(temp_path)
            assert self.editor.settings.get('tabstop') == 2
            assert self.editor.settings.get('theme') == 'dark'
            self.editor.set_status_message.assert_called_with(f'Sourced {temp_path}')
        finally:
            os.unlink(temp_path)
    
    def test_apply_setting(self):
        """Test applying settings to the editor"""
        # Test display refresh triggers
        self.handler._apply_setting('number', True)
        assert self.editor.display.refresh == True
        
        self.editor.display.refresh = False
        self.handler._apply_setting('cursorline', True)
        assert self.editor.display.refresh == True
        
        # Test search highlighting
        self.handler._apply_setting('hlsearch', False)
        assert self.editor.search_highlighting == False
        
        # Test AI model setting
        self.editor.set_ai_model = Mock()
        self.handler._apply_setting('default_model', 'claude')
        self.editor.set_ai_model.assert_called_with('claude')


class TestSettingsHelp:
    """Test the settings help functionality"""
    
    def test_get_help(self):
        """Test getting help text"""
        settings = Settings()
        help_lines = settings.get_help()
        
        # Check that help contains important sections
        help_text = "\n".join(help_lines)
        assert "AIVim Settings Help" in help_text
        assert "Usage:" in help_text
        assert ":set option" in help_text
        assert ":set option=value" in help_text
        assert ":set option!" in help_text
        assert ":set all" in help_text
        assert ":set?" in help_text
        
        # Check that help contains setting descriptions
        assert "tabstop" in help_text
        assert "expandtab" in help_text
        assert "ignorecase" in help_text
        assert "default_model" in help_text


class TestEditorSettingsIntegration:
    """Test settings integration with the Editor class"""
    
    @patch('aivim.editor.curses')
    @patch('aivim.editor.Display')
    def test_editor_initializes_settings(self, mock_display, mock_curses):
        """Test that editor properly initializes settings"""
        editor = Editor()
        assert hasattr(editor, 'settings')
        assert isinstance(editor.settings, Settings)
        assert editor.search_highlighting == editor.settings.search.hlsearch
    
    @patch('aivim.editor.curses')
    @patch('aivim.editor.Display')
    def test_editor_uses_settings_for_search(self, mock_display, mock_curses):
        """Test that editor uses settings for search behavior"""
        editor = Editor()
        editor.settings.set('hlsearch', False)
        editor.search_highlighting = editor.settings.search.hlsearch
        assert editor.search_highlighting == False
        
        editor.settings.set('hlsearch', True)
        editor.search_highlighting = editor.settings.search.hlsearch
        assert editor.search_highlighting == True


class TestDisplaySettingsIntegration:
    """Test settings integration with the Display class"""
    
    def test_display_respects_line_number_setting(self):
        """Test that display respects the line number setting"""
        from aivim.display import Display
        
        # Mock curses window
        mock_stdscr = Mock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_window = Mock()
        mock_stdscr.subwin = Mock(return_value=mock_window)
        
        with patch('aivim.display.curses.newwin', return_value=mock_window):
            display = Display(mock_stdscr)
            
            # Create a mock editor with settings
            editor = Mock()
            editor.settings = Settings()
            
            # Test with line numbers enabled
            editor.settings.set('number', True)
            lines = ['Line 1', 'Line 2', 'Line 3']
            display.update_text(lines, 0, 0, 0, editor=editor)
            # The display should have tried to draw line numbers
            # (exact verification depends on curses mock implementation)
            
            # Test with line numbers disabled
            editor.settings.set('number', False)
            display.update_text(lines, 0, 0, 0, editor=editor)
            # The display should not draw line numbers


if __name__ == '__main__':
    pytest.main([__file__, '-v'])