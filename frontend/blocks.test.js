import test from "node:test";
import assert from "node:assert/strict";
import { ChangeSet } from "@codemirror/state";
import { completedBlock, partialCode, mapTarget } from "./blocks.js";
test("blank line submits exactly one multiline block, whitespace is allowed", () => {
  assert.equal(
    completedBlock("make a function\nand return two\n", 0, 31),
    null,
  );
  const text = "make a function\nand return two\n \n";
  const block = completedBlock(text, 0, text.length);
  assert.equal(block.instruction, "make a function\nand return two");
  assert.equal(completedBlock(text, block.next, text.length), null);
  assert.equal(completedBlock("\n\n", 0, 2), null);
});
test("partial JSON previews decode unicode and escapes without applying invalid JSON", () => {
  assert.equal(partialCode('{"code":"print(\\"Hi\\")\\n界'), 'print("Hi")\n界');
  assert.equal(partialCode('{"code":"a\\u00'), "a");
  assert.equal(partialCode('{"code":"a\\'), "a");
  assert.equal(partialCode('{"explanation":"waiting"}'), "Generating…");
});
test("block anchors move for preceding edits and become stale for edits inside", () => {
  const target = { from: 3, to: 8, invalid: false };
  assert.deepEqual(
    mapTarget(target, ChangeSet.of({ from: 0, insert: "ab" }, 12)),
    { from: 5, to: 10, invalid: false },
  );
  assert.equal(
    mapTarget(target, ChangeSet.of({ from: 5, insert: "x" }, 12)).invalid,
    true,
  );
  assert.equal(
    mapTarget(target, ChangeSet.of({ from: 10, insert: "x" }, 12)).invalid,
    false,
  );
});

test("autoindent after the closing blank line still submits", () => {
  const text = "Create a function:\n    return two\n    \n    ";
  assert.equal(
    completedBlock(text, 0, text.length).instruction,
    "Create a function:\n    return two",
  );
});
