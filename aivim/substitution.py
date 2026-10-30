"""Single parser for Vim substitution delimiters, ranges and flags."""
import re


def parse(command, editor):
    match = re.match(r"^(%|\d+(?:,\d+)?|'<,'>)?s([^\w\s])", command)
    if not match: return None
    spec, delimiter = match.groups(); rest = command[match.end():]
    parts=[]; part=''; escaped=False
    for char in rest:
        if escaped:
            part += char if char == delimiter else '\\' + char; escaped=False
        elif char == '\\': escaped=True
        elif char == delimiter: parts.append(part); part=''
        else: part += char
    if escaped: part += '\\'
    if len(parts) != 2: raise ValueError('Use s/pattern/replacement/flags')
    flags = part
    if any(f not in 'gciI' for f in flags): raise ValueError('Unsupported substitution flag')
    if not parts[0]: raise ValueError('Empty pattern is not supported')
    count = len(editor.buffer.get_lines())
    if spec == '%': bounds=(0,count-1)
    elif spec == "'<,'>":
        a,b=editor.buffer.get_selection()
        if a is None or b is None: raise ValueError('No selection')
        bounds=(min(a[0],b[0]),max(a[0],b[0]))
    elif spec:
        numbers=[int(x)-1 for x in spec.split(',')];bounds=(numbers[0],numbers[-1])
    else: bounds=(editor.cursor_y,editor.cursor_y)
    if not 0 <= bounds[0] <= bounds[1] < count: raise ValueError('Invalid substitution range')
    return parts[0],parts[1],bounds,flags
