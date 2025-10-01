#!/usr/bin/env python3
"""
Performance benchmarks for AIVim editor.
Tests key performance areas: large file operations, rendering, search, and bulk operations.
"""
import os
import sys
import time
import random
import string
import tempfile
import statistics
from typing import List, Tuple, Dict, Any
import functools

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from aivim.buffer import Buffer
from aivim.display import Display
from aivim.syntax import SyntaxHighlighter
from aivim.nlp_mode import NLPHandler


def timeit(func):
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        return result, elapsed_ms
    return wrapper


class PerformanceBenchmark:
    """Main benchmark suite for AIVim performance testing."""
    
    def __init__(self):
        """Initialize the benchmark suite."""
        self.results = {}
        self.large_text = None
        self.very_large_text = None
        
    def generate_large_file(self, lines: int = 10000) -> List[str]:
        """
        Generate a large file with realistic Python code.
        
        Args:
            lines: Number of lines to generate
            
        Returns:
            List of generated lines
        """
        file_lines = []
        
        # Add imports section
        imports = [
            "import os",
            "import sys",
            "import time",
            "import json",
            "import threading",
            "from typing import List, Dict, Optional, Tuple, Any",
            "from collections import defaultdict",
            "",
        ]
        file_lines.extend(imports)
        
        # Generate functions and classes
        templates = [
            lambda i: f"def function_{i}(x: int, y: int = {i}) -> int:",
            lambda i: f"    '''Function {i} documentation string.'''",
            lambda i: f"    result = x * {i} + y",
            lambda i: f"    # Process some complex calculation",
            lambda i: f"    for j in range({i % 10}):",
            lambda i: f"        result += j * {i}",
            lambda i: f"    return result",
            lambda i: "",
            lambda i: f"class MyClass{i}:",
            lambda i: f"    '''Class {i} with various methods and attributes.'''",
            lambda i: f"    ",
            lambda i: f"    def __init__(self, value: int = {i}):",
            lambda i: f"        self.value = value",
            lambda i: f"        self.items = []",
            lambda i: f"        self.cache = {{}}",
            lambda i: "",
            lambda i: f"    def process(self, data: List[Any]) -> Dict[str, Any]:",
            lambda i: f"        '''Process data and return results.'''",
            lambda i: f"        results = {{}}",
            lambda i: f"        for item in data:",
            lambda i: f"            key = str(item)",
            lambda i: f"            results[key] = item * self.value",
            lambda i: f"        return results",
            lambda i: "",
        ]
        
        # Generate lines using templates
        template_count = len(templates)
        current_line = len(file_lines)
        
        while current_line < lines:
            for template_func in templates:
                if current_line >= lines:
                    break
                line = template_func(current_line // template_count)
                file_lines.append(line)
                current_line += 1
        
        return file_lines
    
    @timeit
    def benchmark_buffer_load(self, lines: int = 10000) -> Buffer:
        """
        Benchmark loading a large file into buffer.
        
        Args:
            lines: Number of lines to load
            
        Returns:
            The created buffer
        """
        file_lines = self.generate_large_file(lines)
        content = '\n'.join(file_lines)
        
        buffer = Buffer()
        buffer.set_content(content)
        
        return buffer
    
    @timeit  
    def benchmark_buffer_get_lines(self, buffer: Buffer) -> int:
        """
        Benchmark getting all lines from buffer.
        
        Args:
            buffer: Buffer to test
            
        Returns:
            Number of lines retrieved
        """
        lines = buffer.get_lines()
        return len(lines)
    
    @timeit
    def benchmark_buffer_insert_lines(self, buffer: Buffer, count: int = 100) -> None:
        """
        Benchmark inserting multiple lines.
        
        Args:
            buffer: Buffer to test
            count: Number of lines to insert
        """
        for i in range(count):
            position = random.randint(0, len(buffer.lines) - 1)
            buffer.insert_line(position, f"# Inserted line {i}")
    
    @timeit
    def benchmark_buffer_delete_lines(self, buffer: Buffer, count: int = 100) -> None:
        """
        Benchmark deleting multiple lines.
        
        Args:
            buffer: Buffer to test  
            count: Number of lines to delete
        """
        for i in range(min(count, len(buffer.lines) // 2)):
            if len(buffer.lines) > 1:
                position = random.randint(0, len(buffer.lines) - 1)
                buffer.delete_line(position)
    
    @timeit
    def benchmark_rapid_cursor_movement(self, buffer: Buffer, moves: int = 1000) -> None:
        """
        Benchmark rapid cursor movement operations.
        
        Args:
            buffer: Buffer to test
            moves: Number of cursor moves to perform
        """
        max_y = len(buffer.lines) - 1
        
        for _ in range(moves):
            y = random.randint(0, max_y)
            line = buffer.get_line(y)
            x = random.randint(0, max(0, len(line) - 1))
            # Simulate cursor position update (would be in editor)
            # In real usage, this would trigger display updates
            
    @timeit
    def benchmark_search_in_buffer(self, buffer: Buffer, pattern: str = "def") -> int:
        """
        Benchmark searching for pattern in buffer.
        
        Args:
            buffer: Buffer to search
            pattern: Pattern to search for
            
        Returns:
            Number of matches found
        """
        matches = 0
        lines = buffer.get_lines()
        
        for line_idx, line in enumerate(lines):
            # Find all occurrences in line
            index = 0
            while index < len(line):
                index = line.find(pattern, index)
                if index == -1:
                    break
                matches += 1
                index += len(pattern)
        
        return matches
    
    @timeit
    def benchmark_syntax_highlighting(self, buffer: Buffer, lines_to_highlight: int = 1000) -> None:
        """
        Benchmark syntax highlighting operations.
        
        Args:
            buffer: Buffer to highlight
            lines_to_highlight: Number of lines to process
        """
        highlighter = SyntaxHighlighter()
        highlighter.set_language("test.py")
        
        lines = buffer.get_lines()
        for i in range(min(lines_to_highlight, len(lines))):
            # This simulates what happens during rendering
            highlights = highlighter.highlight(lines[i])
    
    @timeit
    def benchmark_selection_operations(self, buffer: Buffer, operations: int = 100) -> None:
        """
        Benchmark selection operations (visual mode).
        
        Args:
            buffer: Buffer to test
            operations: Number of selection operations
        """
        max_y = len(buffer.lines) - 1
        
        for _ in range(operations):
            # Start selection
            start_y = random.randint(0, max_y // 2)
            start_line = buffer.get_line(start_y)
            start_x = random.randint(0, max(0, len(start_line) - 1))
            buffer.start_selection(start_y, start_x)
            
            # Update selection end
            end_y = random.randint(start_y, min(start_y + 50, max_y))
            end_line = buffer.get_line(end_y)
            end_x = random.randint(0, max(0, len(end_line) - 1))
            buffer.update_selection(end_y, end_x)
            
            # Get selected text
            text = buffer.get_selection_text()
            
            # Clear selection
            buffer.end_selection()
    
    @timeit
    def benchmark_bulk_paste(self, buffer: Buffer, paste_size: int = 1000) -> None:
        """
        Benchmark pasting large amounts of text.
        
        Args:
            buffer: Buffer to test
            paste_size: Number of lines to paste
        """
        # Generate paste content
        paste_lines = [f"# Pasted line {i}" for i in range(paste_size)]
        paste_content = '\n'.join(paste_lines)
        
        # Simulate paste at middle of buffer
        insert_pos = len(buffer.lines) // 2
        current_lines = buffer.get_lines()
        
        # Split at insertion point and rejoin with pasted content
        new_lines = (
            current_lines[:insert_pos] +
            paste_lines +
            current_lines[insert_pos:]
        )
        buffer.set_lines(new_lines)
    
    @timeit
    def benchmark_bulk_delete(self, buffer: Buffer, delete_size: int = 1000) -> None:
        """
        Benchmark deleting large amounts of text.
        
        Args:
            buffer: Buffer to test
            delete_size: Number of lines to delete
        """
        if len(buffer.lines) > delete_size:
            start_pos = len(buffer.lines) // 2
            end_pos = min(start_pos + delete_size, len(buffer.lines))
            
            current_lines = buffer.get_lines()
            new_lines = current_lines[:start_pos] + current_lines[end_pos:]
            buffer.set_lines(new_lines)
    
    def run_all_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """
        Run all benchmarks and collect results.
        
        Returns:
            Dictionary of benchmark results
        """
        print("=" * 60)
        print("AIVim Performance Benchmarks")
        print("=" * 60)
        
        results = {}
        
        # Test different file sizes
        file_sizes = [1000, 5000, 10000, 50000]
        
        for size in file_sizes:
            print(f"\n### Testing with {size} lines ###")
            
            # Buffer loading
            print(f"Loading {size} lines into buffer...")
            buffer, load_time = self.benchmark_buffer_load(size)
            results[f"buffer_load_{size}"] = load_time
            print(f"  Load time: {load_time:.2f}ms")
            
            # Get lines operation
            print("Testing get_lines operation...")
            _, get_time = self.benchmark_buffer_get_lines(buffer)
            results[f"get_lines_{size}"] = get_time
            print(f"  Get lines time: {get_time:.2f}ms")
            
            # Only run detailed tests on reasonable sizes
            if size <= 10000:
                # Insert operations
                print("Testing line insertions...")
                _, insert_time = self.benchmark_buffer_insert_lines(buffer, 100)
                results[f"insert_lines_{size}"] = insert_time
                print(f"  Insert 100 lines: {insert_time:.2f}ms")
                
                # Delete operations
                print("Testing line deletions...")
                _, delete_time = self.benchmark_buffer_delete_lines(buffer, 100)
                results[f"delete_lines_{size}"] = delete_time
                print(f"  Delete 100 lines: {delete_time:.2f}ms")
                
                # Search operations
                print("Testing search operations...")
                matches, search_time = self.benchmark_search_in_buffer(buffer, "def")
                results[f"search_{size}"] = search_time
                print(f"  Search time: {search_time:.2f}ms ({matches} matches)")
                
                # Syntax highlighting
                print("Testing syntax highlighting...")
                _, syntax_time = self.benchmark_syntax_highlighting(buffer, 1000)
                results[f"syntax_highlight_{size}"] = syntax_time
                print(f"  Highlight 1000 lines: {syntax_time:.2f}ms")
                
                # Selection operations
                print("Testing selection operations...")
                _, select_time = self.benchmark_selection_operations(buffer, 50)
                results[f"selection_{size}"] = select_time
                print(f"  50 selections: {select_time:.2f}ms")
                
                # Cursor movement
                print("Testing rapid cursor movement...")
                _, cursor_time = self.benchmark_rapid_cursor_movement(buffer, 1000)
                results[f"cursor_move_{size}"] = cursor_time
                print(f"  1000 cursor moves: {cursor_time:.2f}ms")
        
        # Test bulk operations on medium-sized file
        print("\n### Testing bulk operations (5000 line file) ###")
        buffer, _ = self.benchmark_buffer_load(5000)
        
        print("Testing bulk paste (1000 lines)...")
        _, paste_time = self.benchmark_bulk_paste(buffer, 1000)
        results["bulk_paste_1000"] = paste_time
        print(f"  Paste time: {paste_time:.2f}ms")
        
        print("Testing bulk delete (1000 lines)...")
        _, delete_time = self.benchmark_bulk_delete(buffer, 1000)
        results["bulk_delete_1000"] = delete_time
        print(f"  Delete time: {delete_time:.2f}ms")
        
        return results
    
    def print_summary(self, results: Dict[str, float]) -> None:
        """
        Print a summary of benchmark results.
        
        Args:
            results: Dictionary of benchmark results
        """
        print("\n" + "=" * 60)
        print("Performance Summary")
        print("=" * 60)
        
        # Group results by operation type
        operations = {}
        for key, time_ms in results.items():
            op_type = key.rsplit('_', 1)[0]
            if op_type not in operations:
                operations[op_type] = []
            operations[op_type].append(time_ms)
        
        # Calculate and print statistics
        for op_type, times in operations.items():
            if times:
                avg = statistics.mean(times)
                if len(times) > 1:
                    stdev = statistics.stdev(times)
                    print(f"{op_type}:")
                    print(f"  Average: {avg:.2f}ms")
                    print(f"  Std Dev: {stdev:.2f}ms")
                    print(f"  Min: {min(times):.2f}ms")
                    print(f"  Max: {max(times):.2f}ms")
                else:
                    print(f"{op_type}: {avg:.2f}ms")
        
        # Performance thresholds and warnings
        print("\n" + "=" * 60)
        print("Performance Analysis")
        print("=" * 60)
        
        warnings = []
        
        # Check load times
        if "buffer_load_10000" in results:
            if results["buffer_load_10000"] > 500:
                warnings.append(f"⚠️ Large file load time ({results['buffer_load_10000']:.0f}ms) exceeds 500ms threshold")
        
        # Check search times
        if "search_10000" in results:
            if results["search_10000"] > 100:
                warnings.append(f"⚠️ Search in 10k lines ({results['search_10000']:.0f}ms) exceeds 100ms threshold")
        
        # Check syntax highlighting
        if "syntax_highlight_10000" in results:
            if results["syntax_highlight_10000"] > 200:
                warnings.append(f"⚠️ Syntax highlighting ({results['syntax_highlight_10000']:.0f}ms) exceeds 200ms threshold")
        
        # Check bulk operations
        if "bulk_paste_1000" in results:
            if results["bulk_paste_1000"] > 100:
                warnings.append(f"⚠️ Bulk paste ({results['bulk_paste_1000']:.0f}ms) exceeds 100ms threshold")
        
        if warnings:
            print("Performance warnings:")
            for warning in warnings:
                print(f"  {warning}")
        else:
            print("✅ All operations within acceptable performance thresholds")
        
        # Recommendations
        print("\n" + "=" * 60)
        print("Optimization Recommendations")
        print("=" * 60)
        
        recommendations = []
        
        if "buffer_load_50000" in results and results["buffer_load_50000"] > 1000:
            recommendations.append("• Consider lazy loading for very large files (>50k lines)")
        
        if "get_lines_10000" in results and results["get_lines_10000"] > 10:
            recommendations.append("• Optimize buffer.get_lines() to return reference instead of copy")
        
        if "syntax_highlight_10000" in results and results["syntax_highlight_10000"] > 200:
            recommendations.append("• Cache syntax highlighting results for unchanged lines")
            recommendations.append("• Compile regex patterns once at startup")
        
        if "search_10000" in results and results["search_10000"] > 100:
            recommendations.append("• Implement indexed search for better performance")
            recommendations.append("• Use compiled regex patterns for searches")
        
        if recommendations:
            print("Suggested optimizations:")
            for rec in recommendations:
                print(rec)
        else:
            print("✅ Performance is generally good")


def main():
    """Run the performance benchmark suite."""
    benchmark = PerformanceBenchmark()
    results = benchmark.run_all_benchmarks()
    benchmark.print_summary(results)
    
    # Save results to file for tracking
    import json
    import datetime
    
    timestamp = datetime.datetime.now().isoformat()
    output = {
        "timestamp": timestamp,
        "results": results
    }
    
    with open("performance_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to performance_results.json")


if __name__ == "__main__":
    main()