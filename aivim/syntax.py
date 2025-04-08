"""
Basic syntax highlighting for AIVim
"""
import re
from typing import Dict, List, Tuple


class SyntaxHighlighter:
    """
    Provides basic syntax highlighting for different file types
    """
    def __init__(self):
        # Define regex patterns for different syntax elements
        self.patterns = {
            # Python syntax
            'python': {
                'keywords': re.compile(r'\b(def|class|if|else|elif|for|while|try|except|finally|'
                                      r'with|return|import|from|as|and|or|not|in|is|None|True|False)\b'),
                'strings': re.compile(r'(".*?"|\'.*?\'|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'),
                'comments': re.compile(r'(#.*)'),
                'functions': re.compile(r'\b(\w+)\('),
                'decorators': re.compile(r'(@\w+)'),
            },
            # JavaScript syntax
            'javascript': {
                'keywords': re.compile(r'\b(function|const|let|var|if|else|for|while|try|catch|finally|'
                                     r'return|import|export|class|extends|new|this|super|null|undefined|true|false)\b'),
                'strings': re.compile(r'(".*?"|\'.*?\'|`[\s\S]*?`)'),
                'comments': re.compile(r'(//.*|/\*[\s\S]*?\*/)'),
                'functions': re.compile(r'\b(\w+)\('),
            },
            # HTML syntax
            'html': {
                'tags': re.compile(r'(<[^>]*>)'),
                'attributes': re.compile(r'\s(\w+)='),
                'strings': re.compile(r'(".*?"|\'.*?\')'),
                'comments': re.compile(r'(<!--[\s\S]*?-->)'),
            },
            # Default syntax (basic)
            'default': {
                'keywords': re.compile(r'\b(if|else|for|while|function|return|var|let|const)\b'),
                'strings': re.compile(r'(".*?"|\'.*?\')'),
                'comments': re.compile(r'(//.*|/\*[\s\S]*?\*/|#.*)'),
            },
        }
        
        # File extensions to language mapping
        self.extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.json': 'javascript',
        }
        
        # Current file type (default to Python)
        self.current_language = 'default'
    
    def set_language(self, filename: str) -> None:
        """
        Set the current language based on filename extension
        
        Args:
            filename: The name of the file being edited
        """
        if not filename:
            self.current_language = 'default'
            return
        
        # Get file extension
        for ext, lang in self.extensions.items():
            if filename.endswith(ext):
                self.current_language = lang
                return
        
        # Default if no match
        self.current_language = 'default'
    
    def highlight(self, line: str) -> Dict[int, int]:
        """
        Create a highlighting map for a line of text
        
        Args:
            line: The line of text to highlight
            
        Returns:
            A dictionary mapping character positions to color pairs
        """
        # Default to normal text color
        highlights = {}
        
        # Get patterns for current language
        language_patterns = self.patterns.get(self.current_language, self.patterns['default'])
        
        # Apply each pattern
        for pattern_type, pattern in language_patterns.items():
            for match in pattern.finditer(line):
                # Get the matching text position
                start, end = match.span()
                
                # Assign color based on pattern type
                color = self._get_color_for_pattern_type(pattern_type)
                
                # Apply color to each character in the match
                for i in range(start, end):
                    highlights[i] = color
        
        return highlights
    
    def _get_color_for_pattern_type(self, pattern_type: str) -> int:
        """
        Map pattern types to color pairs
        
        Args:
            pattern_type: The type of pattern (keywords, strings, etc.)
            
        Returns:
            A curses color pair number
        """
        color_map = {
            'keywords': 4,    # Green
            'strings': 5,     # Magenta
            'comments': 6,    # Red
            'functions': 4,   # Green
            'decorators': 4,  # Green
            'tags': 4,        # Green
            'attributes': 5,  # Magenta
        }
        
        return color_map.get(pattern_type, 1)  # Default to white
