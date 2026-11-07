"""Syntax checks that never execute the document."""
import ast
import json
import os
import subprocess


def syntax_check(text, language):
    try:
        if language == 'python': ast.parse(text)
        elif language == 'json': json.loads(text)
        elif language == 'bash':
            result = subprocess.run(['bash', '--noprofile', '--norc', '-n'], input=text,
                                    text=True, capture_output=True, timeout=3,
                                    env={'PATH': os.defpath})
            if result.returncode: return False, result.stderr.strip()[:500]
        else: return None, 'No syntax checker configured for this language.'
    except (SyntaxError, ValueError) as exc: return False, str(exc)[:500]
    except (OSError, subprocess.TimeoutExpired): return None, 'Syntax checker unavailable or timed out.'
    return True, 'Syntax valid. This does not check behavior.'
