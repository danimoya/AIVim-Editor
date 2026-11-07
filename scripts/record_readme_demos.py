"""Record current README tours from the real terminal app and configured model.

Generated code is never executed. All files, recovery and preferences are isolated
in temporary directories. Playback is edited for pace; inference waits are shortened.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import os
from pathlib import Path
import tempfile
import time

os.environ.pop("NO_COLOR", None)

from textual.widgets import Button, Select, SelectionList, TextArea
from textual.widgets.text_area import Selection

from aivim import __version__
from aivim.interface_widgets import MatrixLoading, ProjectPrompt
from aivim.project_widgets import ChangeReview
from aivim.settings import Settings
from aivim.tui import TerminalWorkspace
from record_live_demo import render


class Tour:
    def __init__(self, settings, base, title, filename, *, project=None, startup=False):
        self.base = base
        self.frames = []
        self.last = None
        self.app = TerminalWorkspace(str(filename), settings=settings, project=project,
                                     show_startup=startup)
        self.app.session_store.path = base / "capture-session.json"
        self.app.user_preferences.store.path = base / "capture-preferences.json"
        self.app.recent_files = []
        self.app.reduce_motion = False
        self.app.startup_effect = "matrix"
        self.app.ai_animation = "spinner"
        self.app.title = f"AIVim {__version__} · {title}"

    async def snap(self, pilot, name, duration=1200, *, settle=True):
        if settle:
            await pilot.hover(offset=(2, self.app.size.height - 1))
            await pilot.pause(.12)
        svg = self.app.export_screenshot()
        digest = hashlib.sha256(svg.encode()).hexdigest()
        if digest == self.last:
            path, previous_duration = self.frames[-1]
            self.frames[-1] = (path, previous_duration + duration)
            return
        self.last = digest
        path = self.base / f"{len(self.frames):03d}-{name}.svg"
        path.write_text(svg, encoding="utf-8")
        self.frames.append((path, duration))

    async def type(self, pilot, text):
        for start in range(0, len(text), 4):
            await pilot.press(*text[start:start + 4])
            await self.snap(pilot, "typing", 90, settle=False)

    def report(self, scene, *, model_requests=0, **extra):
        return {
            "release": __version__, "scene": scene,
            "provider": self.app.service.current_model,
            "model": self.app.service.models()[self.app.service.current_model],
            "model_requests": model_requests, "real_terminal_frames": True,
            "screen": [100, 30], "playback_edited_for_pace": True,
            "idle_inference_waits_shortened": bool(model_requests),
            "typing_playback_accelerated": True, "commands_executed": False,
            **extra,
        }


async def workbench(settings, base):
    script = base / "morning.sh"
    script.write_text('#!/usr/bin/env bash\nset -eu\n\nprintf "Good morning, %s!\\n" "${USER:-friend}"\ndate +%F\n')
    tour = Tour(settings, base, "room to think", script)
    app = tour.app
    async with app.run_test(size=(100, 30)) as pilot:
        app.editor.cursor_blink = False
        app.add_source("Writing style", "Use clear, friendly explanations. Keep it concise.")
        app.editor.selection = Selection((1, 0), app.editor.document.end)
        app.say("Select the code. Ask a question. Keep the context you chose.")
        await tour.snap(pilot, "selection", 1400)
        await pilot.press("f2")
        await tour.snap(pilot, "selection-actions", 1200)
        await pilot.click("#choice-query", offset=(2, 0))
        await pilot.pause(.15)
        await tour.type(pilot, "Explain this script in six short bullets.")
        await tour.snap(pilot, "prompt", 1000)
        await pilot.click("#fullscreen-ai")
        await tour.snap(pilot, "fullscreen-controls", 1400)
        await pilot.click("#submit")
        await tour.snap(pilot, "thinking", 350)
        deadline = time.monotonic() + settings.ai.timeout + 10
        previous, captured_at = "", 0
        while app.active and time.monotonic() < deadline:
            await pilot.pause(.08)
            text = app.query_one("#result", TextArea).text
            if text != previous and time.monotonic() - captured_at > .35:
                await tour.snap(pilot, "response-stream", 140)
                previous, captured_at = text, time.monotonic()
        if app.active or not app.records or app.records[0].state != "Answered":
            raise RuntimeError("Workbench request did not complete: " + str([(r.state, r.result[:200]) for r in app.records]))
        await pilot.pause(.25)
        assert app.ai_fullscreen and app.editor.text == script.read_text()
        app.query_one("#result", TextArea).scroll_home(animate=False)
        app.say("Full-screen AI: your prompt on the left, the answer on the right.")
        await tour.snap(pilot, "answer", 2400)
        await pilot.click("#toggle-ai-controls")
        await pilot.pause(.15)
        assert app.ai_controls_collapsed
        app.say("Hide controls for uninterrupted reading · Alt+B brings them back")
        await tour.snap(pilot, "reading", 2400)
        await pilot.press("alt+b")
        await pilot.pause(.15)
        assert not app.ai_controls_collapsed
        app.say("Your prompt and response stay with you when the layout changes.")
        await tour.snap(pilot, "controls-return", 1300)
        await pilot.press("escape")
        await pilot.pause(.15)
        assert not app.ai_fullscreen
        app.say("Esc restores the floating panel. Return to the editor when you are ready.")
        await tour.snap(pilot, "restore", 1300)
    return tour.frames, tour.report("workbench", model_requests=1,
                                   captures=["selection", "contextual actions", "real model streaming",
                                             "full-screen sidebar", "hide/show controls", "Esc restore"])


async def project(settings, base):
    root = base / "greeting"
    root.mkdir()
    script = root / "greet.py"
    script.write_text('def greet(name):\n    return f"Hello, {name}!"\n')
    readme = root / "README.md"
    readme.write_text('# Greeting\n\nCall greet with a name.\n')
    tour = Tour(settings, base, "one thought, several files", script, project=root)
    app = tour.app
    async with app.run_test(size=(100, 30)) as pilot:
        app.editor.cursor_blink = False
        await app.open_document(str(readme))
        readme_id = app.current_id
        await pilot.pause()
        app.say("Click a filename to change buffers. Open files stay within reach.")
        await tour.snap(pilot, "file-tabs", 1200)
        greet_id = next(d.id for d in app.documents.values() if d.name == "greet.py")
        await pilot.click("#buffer-" + greet_id)
        await pilot.pause()
        await app.remove_document(readme_id)
        app.add_source("Project style", "Keep Python small and readable. Document the public function.")
        await pilot.press("f3")
        await tour.snap(pilot, "checked-source", 1300)
        await pilot.press("alt+1")
        app.action_project_generate()
        await pilot.pause(.15)
        assert isinstance(app.screen, ProjectPrompt)
        await tour.type(pilot, "Update @gre")
        await tour.snap(pilot, "open-file-completion", 1300)
        await pilot.press("tab")
        await tour.type(pilot, "and @REA")
        await tour.snap(pilot, "recent-file-completion", 1300)
        await pilot.press("tab", "enter")
        await tour.type(pilot, 'Make greet default to "World" and add a short docstring.')
        await pilot.press("enter")
        await tour.type(pilot, 'README: show greet() and greet("Ada") examples.')
        await pilot.press("enter")
        await tour.type(pilot, "Only change these two files.")
        await tour.snap(pilot, "multiline-instructions", 1900)
        await pilot.click("#project-prompt-submit")
        app.say("Preparing a project proposal. Files stay unchanged until review.")
        await tour.snap(pilot, "preparing-proposal", 450)
        deadline = time.monotonic() + settings.ai.timeout + 10
        while time.monotonic() < deadline:
            await pilot.pause(.1)
            if isinstance(app.screen, ChangeReview):
                break
            if not app.project_busy:
                raise RuntimeError("Project proposal failed: " + str(app.query_one("#status").render()))
        if not isinstance(app.screen, ChangeReview):
            raise RuntimeError("Project proposal timed out")
        plan = app.screen.changeset
        assert {change.path for change in plan.changes} == {"greet.py", "README.md"}
        assert "World" not in script.read_text()
        await pilot.pause(.25)
        await tour.snap(pilot, "review-project", 2000)
        hunks = app.screen.query_one("#change-hunks", SelectionList)
        hunks.focus()
        await pilot.press("end")
        await tour.snap(pilot, "review-second-file", 1600)
        await pilot.click("#changes-apply")
        await pilot.pause(.3)
        ast.parse(script.read_text())
        assert "World" in script.read_text() and app.last_checkpoint
        await app.open_document(str(readme))
        app.say("Checked hunks applied. A checkpoint is ready if you want to roll back.")
        await tour.snap(pilot, "updated-readme", 1800)
        await pilot.click("#buffer-" + greet_id)
        await pilot.pause(.15)
        await tour.snap(pilot, "updated-python", 2000)
    return tour.frames, tour.report("project", model_requests=1,
                                   files=["greet.py", "README.md"], review_required=True,
                                   captures=["file tabs", "checked sources", "open/recent @ completion",
                                             "five-line prompt", "multi-file review", "explicit acceptance", "checkpoint"])


async def controls(settings, base):
    script = base / "hello.sh"
    script.write_text('#!/usr/bin/env bash\n\nprintf "Hello, terminal.\\n"\n')
    tour = Tour(settings, base, "make it yours", script, startup=True)
    app = tour.app
    async with app.run_test(size=(100, 30)) as pilot:
        for _ in range(7):
            await pilot.pause(.045)
            if isinstance(app.screen, MatrixLoading):
                await tour.snap(pilot, "matrix-startup", 90, settle=False)
        await pilot.pause(.7)
        app.editor.cursor_blink = False
        app.say("One title row. One status row. The rest is your editor.")
        await tour.snap(pilot, "minimal-editor", 1400)
        for name in ["live-review", "live-auto", "edit"]:
            await pilot.click("#live-mode")
            await tour.snap(pilot, name, 1100)
        app.action_settings()
        await pilot.pause(.15)
        await tour.snap(pilot, "editing-defaults", 1700)
        selector = app.screen.query_one("#setting-streaming", Select)
        selector.scroll_visible(animate=False)
        await pilot.wait_for_scheduled_animations()
        await pilot.click(selector)
        await tour.snap(pilot, "streaming-effects", 1800)
        await pilot.press("end", "enter")
        await tour.snap(pilot, "matrix-effect-choice", 1400)
        button = app.screen.query_one("#settings-save", Button)
        button.scroll_visible(animate=False)
        await pilot.wait_for_scheduled_animations()
        await pilot.click(button)
        await pilot.pause(.15)
        assert app.streaming_effect == "matrix"
        app.say("Your keys. Your effects. Reduced motion is a setting away.")
        await tour.snap(pilot, "settings-saved", 1700)
    return tour.frames, tour.report("controls",
                                   captures=["Matrix startup", "minimal editor", "rotating live modes",
                                             "user settings", "typing/instant/Matrix effect choice"])


async def main_async(args):
    for name in (["workbench", "project", "controls"] if args.scene == "all" else [args.scene]):
        settings = Settings(args.config)
        if args.provider:
            settings.ai.default_model = args.provider
        settings.ai.max_tokens = min(settings.ai.max_tokens, 2048)
        with tempfile.TemporaryDirectory(prefix="aivim-readme-" + name + "-") as directory:
            frames, report = await globals()[name](settings, Path(directory))
            output = Path(args.output_dir) / f"{name}-{__version__}.gif"
            await render(frames, output, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=["all", "workbench", "project", "controls"], default="all")
    parser.add_argument("--config")
    parser.add_argument("--provider")
    parser.add_argument("--output-dir", default="docs/assets")
    asyncio.run(main_async(parser.parse_args()))
