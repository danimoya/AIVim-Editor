#!/usr/bin/env python3
"""
Comprehensive tests for file operations in AIVim
"""
import os
import sys
import unittest
import tempfile
import shutil
import stat
from unittest.mock import MagicMock, Mock, patch, PropertyMock, mock_open

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor, Tab
from aivim.buffer import Buffer
from aivim.command_handler import CommandHandler
from aivim.file_browser import FileBrowser, FileBrowserItem


class TestFileOperations(unittest.TestCase):
    """Test file operations functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        self.test_content = "This is a test file\nLine 2\nLine 3"
        
        # Create a test file
        with open(self.test_file, 'w') as f:
            f.write(self.test_content)
        
        # Create editor instance
        self.editor = Editor()
        self.editor.display = MagicMock()
        self.editor.set_status_message = MagicMock()  # Mock set_status_message
        self.editor.command_handler = CommandHandler(self.editor)
        
        # Mock the auto_backup attribute
        self.editor.auto_backup = False  # Disable for tests
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass
    
    # Test basic file loading
    def test_load_file_existing(self):
        """Test loading an existing file"""
        self.editor.load_file(self.test_file)
        
        self.assertEqual(self.editor.filename, self.test_file)
        self.assertEqual(self.editor.buffer.get_content(), self.test_content)
        self.assertFalse(self.editor.buffer.is_modified())
    
    def test_load_file_nonexistent(self):
        """Test loading a non-existent file (new file)"""
        new_file = os.path.join(self.test_dir, "new.txt")
        self.editor.load_file(new_file)
        
        self.assertEqual(self.editor.filename, new_file)
        self.assertEqual(self.editor.buffer.get_content(), "")
        self.assertFalse(self.editor.buffer.is_modified())
    
    def test_load_file_with_error(self):
        """Test loading file with read error"""
        # Create a file that can't be read
        unreadable_file = os.path.join(self.test_dir, "unreadable.txt")
        with open(unreadable_file, 'w') as f:
            f.write("test")
        os.chmod(unreadable_file, 0o000)
        
        # Try to load it
        self.editor.load_file(unreadable_file)
        
        # Should handle error gracefully
        self.editor.set_status_message.assert_called()
        
        # Cleanup
        os.chmod(unreadable_file, 0o644)
    
    # Test file saving
    def test_save_file_basic(self):
        """Test basic file saving"""
        self.editor.filename = self.test_file
        self.editor.buffer.set_content("New content")
        self.editor.buffer.modified = True
        
        self.editor.save_file()
        
        # Check file was saved
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "New content")
        self.assertFalse(self.editor.buffer.is_modified())
    
    def test_save_file_with_filename(self):
        """Test saving to a different filename"""
        new_file = os.path.join(self.test_dir, "saved.txt")
        self.editor.buffer.set_content("Saved content")
        
        self.editor.save_file(new_file)
        
        # Check file was saved
        self.assertTrue(os.path.exists(new_file))
        with open(new_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Saved content")
        self.assertEqual(self.editor.filename, new_file)
    
    def test_save_file_with_backup(self):
        """Test saving with backup creation"""
        self.editor.auto_backup = True
        self.editor.filename = self.test_file
        self.editor.buffer.set_content("Updated content")
        
        self.editor.save_file()
        
        # Check for backup files
        backup_files = [f for f in os.listdir(self.test_dir) if f.startswith('.test.txt.')]
        self.assertTrue(len(backup_files) > 0, "No backup file created")
    
    def test_save_file_permission_denied(self):
        """Test saving to a read-only file"""
        # Make file read-only
        os.chmod(self.test_file, 0o444)
        
        self.editor.filename = self.test_file
        self.editor.buffer.set_content("Cannot save this")
        
        self.editor.save_file()
        
        # Should show error message
        self.editor.set_status_message.assert_called()
        status_msg = self.editor.set_status_message.call_args[0][0]
        self.assertIn("Permission denied", status_msg)
        
        # Cleanup
        os.chmod(self.test_file, 0o644)
    
    def test_save_file_disk_full(self):
        """Test handling disk full error"""
        with patch('builtins.open', side_effect=OSError(28, "No space left on device")):
            self.editor.filename = self.test_file
            self.editor.buffer.set_content("Content")
            
            self.editor.save_file()
            
            # Should show disk full error
            self.editor.set_status_message.assert_called()
            status_msg = self.editor.set_status_message.call_args[0][0]
            self.assertIn("Disk full", status_msg)
    
    # Test reload functionality
    def test_reload_file(self):
        """Test reloading file from disk"""
        self.editor.filename = self.test_file
        self.editor.buffer.set_content("Modified content")
        self.editor.buffer.modified = True
        
        # Modify file on disk
        with open(self.test_file, 'w') as f:
            f.write("External change")
        
        # Should fail without force (buffer modified)
        with self.assertRaises(ValueError):
            self.editor.reload_file()
        
        # Should work with force
        self.editor.reload_file(force=True)
        self.assertEqual(self.editor.buffer.get_content(), "External change")
        self.assertFalse(self.editor.buffer.is_modified())
    
    def test_reload_file_nonexistent(self):
        """Test reloading when file doesn't exist"""
        self.editor.filename = "/nonexistent/file.txt"
        
        with self.assertRaises(FileNotFoundError):
            self.editor.reload_file()
    
    # Test binary file detection
    def test_is_binary_file_text(self):
        """Test binary detection on text file"""
        self.assertFalse(self.editor.is_binary_file(self.test_file))
    
    def test_is_binary_file_binary(self):
        """Test binary detection on binary file"""
        binary_file = os.path.join(self.test_dir, "binary.bin")
        with open(binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')
        
        self.assertTrue(self.editor.is_binary_file(binary_file))
    
    def test_is_binary_file_nonexistent(self):
        """Test binary detection on non-existent file"""
        self.assertFalse(self.editor.is_binary_file("/nonexistent/file"))
    
    # Test permission checking
    def test_load_file_with_permissions_check(self):
        """Test loading file with permission checking"""
        self.editor.load_file_with_permissions_check(self.test_file)
        
        self.assertEqual(self.editor.filename, self.test_file)
        self.assertEqual(self.editor.buffer.get_content(), self.test_content)
    
    def test_load_file_with_permissions_check_readonly(self):
        """Test loading read-only file with warning"""
        # Make file read-only
        os.chmod(self.test_file, 0o444)
        
        self.editor.load_file_with_permissions_check(self.test_file)
        
        # Should show warning
        self.editor.set_status_message.assert_called()
        status_msg = self.editor.set_status_message.call_args[0][0]
        self.assertIn("read-only", status_msg)
        
        # Cleanup
        os.chmod(self.test_file, 0o644)
    
    def test_load_file_with_permissions_check_binary(self):
        """Test loading binary file is prevented"""
        binary_file = os.path.join(self.test_dir, "binary.bin")
        with open(binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')
        
        with self.assertRaises(ValueError):
            self.editor.load_file_with_permissions_check(binary_file)
    
    # Test command handlers
    def test_cmd_edit_file(self):
        """Test :e filename command"""
        new_file = os.path.join(self.test_dir, "another.txt")
        with open(new_file, 'w') as f:
            f.write("Another file")
        
        result = self.editor.command_handler.execute(f":e {new_file}")
        
        self.assertTrue(result)
        self.assertEqual(self.editor.filename, new_file)
        self.assertEqual(self.editor.buffer.get_content(), "Another file")
    
    def test_cmd_edit_current(self):
        """Test :e command (reload current)"""
        self.editor.filename = self.test_file
        self.editor.load_file(self.test_file)
        
        result = self.editor.command_handler.execute(":e")
        
        self.assertTrue(result)
        self.assertEqual(self.editor.buffer.get_content(), self.test_content)
    
    def test_cmd_force_edit(self):
        """Test :e! command"""
        self.editor.filename = self.test_file
        self.editor.buffer.set_content("Modified")
        self.editor.buffer.modified = True
        
        result = self.editor.command_handler.execute(":e!")
        
        self.assertTrue(result)
        self.assertEqual(self.editor.buffer.get_content(), self.test_content)
        self.assertFalse(self.editor.buffer.is_modified())
    
    def test_cmd_new_buffer(self):
        """Test :new command"""
        initial_tabs = len(self.editor.tabs)
        
        result = self.editor.command_handler.execute(":new")
        
        self.assertTrue(result)
        self.assertEqual(len(self.editor.tabs), initial_tabs + 1)
        self.assertEqual(self.editor.current_tab.name, "Untitled")
    
    def test_cmd_new_buffer_named(self):
        """Test :new name command"""
        initial_tabs = len(self.editor.tabs)
        
        result = self.editor.command_handler.execute(":new MyBuffer")
        
        self.assertTrue(result)
        self.assertEqual(len(self.editor.tabs), initial_tabs + 1)
        self.assertEqual(self.editor.current_tab.name, "MyBuffer")
    
    def test_cmd_saveas(self):
        """Test :saveas command"""
        self.editor.buffer.set_content("Save as content")
        new_file = os.path.join(self.test_dir, "saveas.txt")
        
        result = self.editor.command_handler.execute(f":saveas {new_file}")
        
        self.assertTrue(result)
        self.assertEqual(self.editor.filename, new_file)
        self.assertTrue(os.path.exists(new_file))
        
        with open(new_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Save as content")
    
    def test_cmd_saveas_permission_denied(self):
        """Test :saveas to read-only directory"""
        # Create a read-only directory
        readonly_dir = os.path.join(self.test_dir, "readonly")
        os.mkdir(readonly_dir)
        os.chmod(readonly_dir, 0o555)
        
        new_file = os.path.join(readonly_dir, "file.txt")
        result = self.editor.command_handler.execute(f":saveas {new_file}")
        
        self.assertFalse(result)
        
        # Cleanup
        os.chmod(readonly_dir, 0o755)
    
    # Test file browser
    def test_file_browser_item(self):
        """Test FileBrowserItem class"""
        item = FileBrowserItem(self.test_file, is_dir=False)
        
        self.assertEqual(item.name, "test.txt")
        self.assertFalse(item.is_dir)
        self.assertGreater(item.size, 0)
        self.assertIsNotNone(item.modified_time)
    
    def test_file_browser_item_directory(self):
        """Test FileBrowserItem for directory"""
        item = FileBrowserItem(self.test_dir, is_dir=True)
        
        self.assertEqual(item.name, os.path.basename(self.test_dir))
        self.assertTrue(item.is_dir)
    
    def test_file_browser_item_display(self):
        """Test FileBrowserItem display string"""
        item = FileBrowserItem(self.test_file, is_dir=False)
        display_str = item.get_display_string(80)
        
        self.assertIn("test.txt", display_str)
        self.assertIn("B", display_str)  # Size indicator
    
    def test_file_browser_init(self):
        """Test FileBrowser initialization"""
        browser = FileBrowser(self.editor)
        
        self.assertEqual(browser.current_path, os.getcwd())
        self.assertEqual(browser.selected_index, 0)
        self.assertFalse(browser.show_hidden)
        self.assertEqual(browser.filter_text, "")
    
    @patch('aivim.file_browser.os.listdir')
    def test_file_browser_load_directory(self, mock_listdir):
        """Test loading directory contents"""
        mock_listdir.return_value = ['file1.txt', 'file2.txt', '.hidden']
        
        browser = FileBrowser(self.editor)
        browser._load_directory()
        
        # Should have parent dir + 2 visible files (hidden excluded by default)
        self.assertEqual(len(browser.items), 3)
    
    @patch('aivim.file_browser.os.listdir')
    def test_file_browser_load_directory_with_hidden(self, mock_listdir):
        """Test loading directory with hidden files shown"""
        mock_listdir.return_value = ['file1.txt', '.hidden']
        
        browser = FileBrowser(self.editor)
        browser.show_hidden = True
        browser._load_directory()
        
        # Should have parent dir + 2 files (including hidden)
        self.assertEqual(len(browser.items), 3)
    
    @patch('aivim.file_browser.os.listdir')
    def test_file_browser_filter(self, mock_listdir):
        """Test filtering files in browser"""
        mock_listdir.return_value = ['test.txt', 'data.csv', 'readme.md']
        
        browser = FileBrowser(self.editor)
        browser.filter_text = "test"
        browser._load_directory()
        
        # Should only have parent dir + test.txt
        self.assertEqual(len(browser.items), 2)
    
    # Integration tests
    def test_full_edit_save_cycle(self):
        """Test complete edit and save cycle"""
        # Load file
        self.editor.load_file(self.test_file)
        original_content = self.editor.buffer.get_content()
        
        # Modify content
        self.editor.buffer.set_content("Modified content\nNew line")
        self.assertTrue(self.editor.buffer.is_modified())
        
        # Save file
        self.editor.save_file()
        self.assertFalse(self.editor.buffer.is_modified())
        
        # Reload and verify
        self.editor.reload_file()
        self.assertEqual(self.editor.buffer.get_content(), "Modified content\nNew line")
    
    def test_multiple_file_operations(self):
        """Test switching between multiple files"""
        file1 = os.path.join(self.test_dir, "file1.txt")
        file2 = os.path.join(self.test_dir, "file2.txt")
        
        with open(file1, 'w') as f:
            f.write("File 1 content")
        with open(file2, 'w') as f:
            f.write("File 2 content")
        
        # Load first file
        self.editor.load_file(file1)
        self.assertEqual(self.editor.buffer.get_content(), "File 1 content")
        
        # Switch to second file
        self.editor.load_file_with_permissions_check(file2, force=True)
        self.assertEqual(self.editor.buffer.get_content(), "File 2 content")
        
        # Save changes
        self.editor.buffer.set_content("File 2 modified")
        self.editor.save_file()
        
        # Verify saved content
        with open(file2, 'r') as f:
            content = f.read()
        self.assertEqual(content, "File 2 modified")
    
    def test_error_recovery(self):
        """Test recovery from various error conditions"""
        # Try to save without filename
        self.editor.filename = None
        self.editor.save_file()
        # Should not crash
        
        # Try to reload without filename
        self.editor.filename = None
        with self.assertRaises(ValueError):
            self.editor.reload_file()
        # Should raise but not crash
        
        # Try to load non-existent file
        self.editor.load_file("/nonexistent/path/file.txt")
        # Should handle gracefully


class TestCommandIntegration(unittest.TestCase):
    """Test file commands integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.editor = Editor()
        self.editor.display = MagicMock()
        self.editor.set_status_message = MagicMock()  # Mock set_status_message
        self.editor.command_handler = CommandHandler(self.editor)
        self.editor.auto_backup = False
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_command_chaining(self):
        """Test chaining multiple file commands"""
        file1 = os.path.join(self.test_dir, "test1.txt")
        file2 = os.path.join(self.test_dir, "test2.txt")
        
        # Create new buffer
        self.editor.command_handler.execute(":new")
        
        # Add content
        self.editor.buffer.set_content("Test content")
        
        # Save as file1
        self.editor.command_handler.execute(f":w {file1}")
        self.assertTrue(os.path.exists(file1))
        
        # Save as file2
        self.editor.command_handler.execute(f":saveas {file2}")
        self.assertTrue(os.path.exists(file2))
        
        # Both files should exist with same content
        with open(file1, 'r') as f:
            content1 = f.read()
        with open(file2, 'r') as f:
            content2 = f.read()
        
        self.assertEqual(content1, content2)
        self.assertEqual(content1, "Test content")


if __name__ == '__main__':
    unittest.main()