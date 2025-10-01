"""
Basic syntax highlighting for AIVim
"""
import re
from typing import Dict, List, Tuple


class SyntaxHighlighter:
    """
    Provides basic syntax highlighting for different file types
    """
    # Class-level compiled patterns for performance (compiled once, reused many times)
    _compiled_patterns = None
    
    def __init__(self):
        # Performance optimization: Use class-level compiled patterns
        if SyntaxHighlighter._compiled_patterns is None:
            SyntaxHighlighter._compiled_patterns = self._compile_patterns()
        
        self.patterns = SyntaxHighlighter._compiled_patterns
        
        # Line-level cache for highlighted lines
        self._highlight_cache = {}  # Cache: {(line_hash, language): highlights}
        self._cache_hits = 0  # Track cache performance
        self._cache_misses = 0
        
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
    
    @staticmethod
    def _compile_patterns():
        """Compile all regex patterns once at startup"""
        return {
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
                # Clear cache when switching languages
                self._highlight_cache.clear()
                return
        
        # Default if no match
        self.current_language = 'default'
    
    def highlight(self, line: str) -> Dict[int, int]:
        """
        Create a highlighting map for a line of text - with caching for performance
        
        Args:
            line: The line of text to highlight
            
        Returns:
            A dictionary mapping character positions to color pairs
        """
        # Performance optimization: Cache highlighted lines
        cache_key = (hash(line), self.current_language)
        
        if cache_key in self._highlight_cache:
            self._cache_hits += 1
            return self._highlight_cache[cache_key]
        
        self._cache_misses += 1
        
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
        
        # Cache the result (limit cache size to prevent memory issues)
        if len(self._highlight_cache) > 10000:  # Clear cache if it gets too large
            self._highlight_cache.clear()
        
        self._highlight_cache[cache_key] = highlights
        
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
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache performance statistics
        
        Returns:
            Dictionary with cache hits, misses, and hit rate
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_size': len(self._highlight_cache),
            'hit_rate': hit_rate
        }
    
    def clear_cache(self) -> None:
        """Clear the highlight cache"""
        self._highlight_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0