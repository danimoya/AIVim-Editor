"""Deterministic output-language inference; no model call or project file reads."""
from collections import Counter
from pathlib import Path
import re

EXTENSIONS = {
    '.py': 'python', '.pyw': 'python', '.sh': 'bash', '.bash': 'bash', '.zsh': 'zsh',
    '.fish': 'fish', '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.jsx': 'javascript', '.ts': 'typescript', '.tsx': 'typescript', '.rs': 'rust',
    '.go': 'go', '.rb': 'ruby', '.lua': 'lua', '.java': 'java', '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.hpp': 'cpp', '.cs': 'csharp', '.json': 'json',
    '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml', '.sql': 'sql', '.md': 'markdown',
    '.html': 'html', '.htm': 'html', '.css': 'css', '.xml': 'xml', '.ps1': 'powershell',
}
ALIASES = {'shell': 'bash', 'bash': 'bash', 'zsh': 'zsh', 'fish': 'fish',
    'python': 'python', 'javascript': 'javascript', 'typescript': 'typescript',
    'rust': 'rust', 'golang': 'go', 'go': 'go', 'ruby': 'ruby', 'lua': 'lua',
    'java': 'java', 'c++': 'cpp', 'c#': 'csharp', 'c': 'c', 'json': 'json',
    'yaml': 'yaml', 'toml': 'toml', 'sql': 'sql', 'markdown': 'markdown',
    'html': 'html', 'css': 'css', 'powershell': 'powershell'}
LANGUAGE_PATTERN = '|'.join(re.escape(n) for n in sorted(ALIASES, key=len, reverse=True))


def filename_language(name, saved=False):
    if not saved and re.fullmatch(r'untitled-\d+\.py', name):
        return None
    path = Path(name)
    if path.name in {'Dockerfile', 'Containerfile'}: return 'dockerfile'
    return EXTENSIONS.get(path.suffix.lower())


def content_language(content):
    shell = re.match(r'^#!.*\b(bash|zsh|fish|sh)\b', content)
    if shell: return 'bash' if shell[1] == 'sh' else shell[1]
    if re.match(r'^#!.*\bpython[\d.]*\b', content): return 'python'
    patterns = [
        ('python', r'(?m)^\s*(?:async\s+def\s+|def\s+\w+\(|from\s+\w+\s+import\s|import\s+\w+\s*$|print\s*\()'),
        ('bash', r'(?m)^\s*(?:echo\s+|(?:export\s+)?[A-Z_][A-Z_\d]*=|if\s+\[|set\s+-[a-z]+|function\s+\w+)'),
        ('rust', r'(?m)^\s*(?:fn\s+\w+\(|use\s+\w+::|impl\s+\w+)'),
        ('go', r'(?m)^\s*(?:package\s+\w+|func\s+\w+\()'),
        ('typescript', r'(?m)^\s*(?:interface\s+\w+|type\s+\w+\s*=)'),
        ('javascript', r'(?m)^\s*(?:export\s+(?:default\s+)?|(?:const|let|var)\s+\w+\s*=|(?:async\s+)?function\s+\w+)'),
        ('html', r'(?i)<!doctype\s+html|<html\b'),
    ]
    for language, pattern in patterns:
        if re.search(pattern, content[:16000]): return language
    if content.lstrip().startswith(('{', '[')):
        import json
        try: json.loads(content); return 'json'
        except (ValueError, RecursionError): pass
    return None


def prompt_language(prompt):
    # Output wording outranks references to an input language or source filename.
    patterns = [
        rf'\b(?:convert|translate|rewrite)\b[^\n]{{0,100}}?\b(?:to|into)\s+({LANGUAGE_PATTERN})(?![\w+#])',
        rf'\b(?:in|using|use)\s+({LANGUAGE_PATTERN})(?![\w+#])',
        rf'\b(?:write|create|generate)\s+(?:(?:a|an|new|simple|small)\s+)*({LANGUAGE_PATTERN})(?![\w+#])',
        rf'\b({LANGUAGE_PATTERN})\s+(?:script|program|function|code|module)\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.I)
        if match: return ALIASES[match[1].lower()]
    return None


def infer_language(name, content='', prompt='', opened=(), saved=False):
    explicit = prompt_language(prompt)
    if explicit: return explicit
    extension = filename_language(name, saved)
    detected = content_language(content)
    if content.startswith('#!') and detected: return detected
    if extension: return extension
    if detected: return detected
    inline = content_language(prompt)
    if inline: return inline
    votes = Counter()
    for other_name, other_content, other_saved in opened:
        language = filename_language(other_name, other_saved) or content_language(other_content)
        if language: votes[language] += 1
    if votes: return votes.most_common(1)[0][0]
    return 'plain text'


def highlight_language(language, available):
    language = {'typescript': 'javascript', 'zsh': 'bash', 'fish': 'bash'}.get(language, language)
    return language if language in available else None
