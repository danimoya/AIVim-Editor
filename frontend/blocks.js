// A typed empty line closes a block; ordinary newlines keep accumulating it.
export function completedBlock(text, start, head) {
  if (start === null || start > head) return null;
  const value = text.slice(start, head),
    match = /\n[ \t]*\n[ \t]*$/.exec(value);
  if (!match) return null;
  const instruction = value.slice(0, match.index);
  if (!instruction.trim()) return null;
  return { from: start, to: start + match.index, instruction, next: head };
}
// Preview a JSON code string before the full structured proposal is available.
// Decode only complete escape sequences; final application always uses server validation.
export function partialCode(raw) {
  const match = /"code"\s*:\s*"/.exec(raw);
  if (!match) return "Generating…";
  let encoded = "",
    escaped = false;
  for (const char of raw.slice(match.index + match[0].length)) {
    if (char === '"' && !escaped) break;
    encoded += char;
    if (char === "\\") escaped = !escaped;
    else escaped = false;
  }
  while (encoded.length) {
    try {
      return JSON.parse('"' + encoded + '"');
    } catch {
      encoded = encoded.slice(0, -1);
    }
  }
  return "";
}
export function mapTarget(target, changes) {
  let invalid = target.invalid;
  changes.iterChangedRanges((from, to) => {
    if (
      from === to
        ? from >= target.from && from <= target.to
        : from < target.to && to > target.from
    )
      invalid = true;
  });
  return {
    from: changes.mapPos(target.from, 1),
    to: changes.mapPos(target.to, -1),
    invalid,
  };
}
