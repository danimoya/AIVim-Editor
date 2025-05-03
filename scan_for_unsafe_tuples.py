#!/usr/bin/env python3

"""
Scan the codebase for potentially unsafe tuple unpacking in comprehensions and loops
"""

import os
import re

def scan_file(file_path):
    """Scan a single file for unsafe tuple unpacking"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    # Find all list comprehensions, generator expressions, and for loops that might do tuple unpacking
    # Looking for patterns like:
    # (a, b) or a, b in something
    # (start, end) or start, end in something
    patterns = [
        r'for\s+\(\s*\w+\s*,\s*\w+\s*\)\s+in\s+[\w\.\[\]\(\)]+', # for (a, b) in something
        r'for\s+\w+\s*,\s*\w+\s+in\s+[\w\.\[\]\(\)]+',  # for a, b in something
        r'\(.*for\s+\(\s*\w+\s*,\s*\w+\s*\)\s+in\s+[\w\.\[\]\(\)]+.*\)', # (... for (a, b) in something ...)
        r'\(.*for\s+\w+\s*,\s*\w+\s+in\s+[\w\.\[\]\(\)]+.*\)',  # (... for a, b in something ...)
    ]
    
    line_number = 0
    lines = content.split('\n')
    issues = []
    
    for i, line in enumerate(lines):
        line_number = i + 1
        for pattern in patterns:
            if re.search(pattern, line):
                # Check if the line contains a reference to self.nlp_sections or has a tuple variable
                if 'self.nlp_sections' in line or 'tuple' in line or '_sections' in line or 'section' in line:
                    issues.append((line_number, line.strip()))
                
    return issues

def scan_directory(dir_path, file_extension='.py'):
    """Scan a directory for files with the specified extension"""
    all_issues = {}
    
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(file_extension):
                file_path = os.path.join(root, file)
                issues = scan_file(file_path)
                if issues:
                    all_issues[file_path] = issues
    
    return all_issues

def main():
    """Main function"""
    print("Scanning for potentially unsafe tuple unpacking...\n")
    
    # Scan the main directories
    all_issues = {}
    for directory in ['.', 'aivim', 'tests']:
        if os.path.exists(directory):
            issues = scan_directory(directory)
            all_issues.update(issues)
    
    # Print the results
    if all_issues:
        print(f"Found {sum(len(issues) for issues in all_issues.values())} potential issues in {len(all_issues)} files:")
        for file_path, issues in all_issues.items():
            print(f"\n{file_path}:")
            for line_number, line in issues:
                print(f"  Line {line_number}: {line}")
    else:
        print("No potential issues found.")

if __name__ == "__main__":
    main()
