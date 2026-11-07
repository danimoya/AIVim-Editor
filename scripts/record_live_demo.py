"""Record real live Bash replacements; shorten idle inference pauses, never fake output.

Install .[demo,terminal-syntax], then `python -m playwright install chromium`.
This uses the configured model. Generated Bash is checked with `bash -n`, not executed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

# The capture should reflect the app's palette even in a NO_COLOR build shell.
os.environ.pop("NO_COLOR", None)

from aivim import __version__
from aivim.settings import Settings
from aivim.tui import TerminalWorkspace
from textual.widgets import Checkbox

PROMPTS = [
    "Print Hello.",
    "Show the current directory disk usage in human-readable form.",
    "Count regular files in the current directory, without recursion.",
]


async def capture(settings, directory):
    app = TerminalWorkspace(settings=settings)
    app.title = "AIVim " + __version__ + " · write in a rhythm"
    frames = []
    last = None

    def snapshot(duration=80, force=False):
        nonlocal last
        svg = app.export_screenshot()
        digest = hashlib.sha256(svg.encode()).hexdigest()
        if digest == last and not force:
            return
        last = digest
        path = directory / f"{len(frames):04d}.svg"
        path.write_text(svg, encoding="utf-8")
        frames.append((path, duration))

    async with app.run_test(size=(100, 28)) as pilot:
        app.document.name = "live-demo.sh"
        app.editor.language = "bash"
        app.editor.cursor_blink = False
        if app.editor.vim_enabled: await pilot.press("f4")
        app.query_one("#live", Checkbox).value = True
        app.query_one("#auto", Checkbox).value = True
        await pilot.pause()
        app.editor.focus()
        app.say("Type a Bash instruction · blank line submits · output replaces it when ready")
        snapshot(900)
        for prompt in PROMPTS:
            for start in range(0, len(prompt), 3):
                await pilot.press(*prompt[start : start + 3])
                snapshot(75)
            snapshot(450, force=True)
            await pilot.press("enter", "enter")
            snapshot(180)
            # Keep typing the next prompt while an earlier one may still be generating.
        deadline = time.monotonic() + settings.ai.timeout * len(PROMPTS) + 5
        while time.monotonic() < deadline:
            await pilot.pause(0.04)
            snapshot(100)
            if len(app.records) == len(PROMPTS) and not app.active and not app.pending and not app.proposal:
                break
        records = list(reversed(app.records))
        if len(records) != len(PROMPTS) or any(record.state != "Accepted" for record in records):
            raise RuntimeError("Demo failed: " + str([(r.state, r.result[:160]) for r in records]))
        code = app.editor.text
        if any(prompt in code for prompt in PROMPTS):
            raise RuntimeError("An instruction was not replaced")
        subprocess.run(["bash", "-n"], input=code, text=True, check=True)
        app.say(
            "Three live replacements complete · Bash syntax checked · commands were not executed"
        )
        snapshot(2300, force=True)
        report = {
            "release": __version__,
            "provider": app.service.current_model,
            "model": app.service.models()[app.service.current_model],
            "screen": [100, 28],
            "idle_inference_waits_shortened": True,
            "commands_executed": False,
            "blocks": [{"instruction": r.instruction, "code": r.replacement} for r in records],
        }
    return frames, report


async def render(frames, output, report):
    from PIL import Image
    from playwright.async_api import async_playwright

    images = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1500, "height": 1000})
        await page.route("https://**", lambda route: route.abort())
        for index, (path, _) in enumerate(frames):
            svg = re.sub(r"@font-face\s*\{.*?\}", "", path.read_text(), flags=re.S)
            await page.set_content(svg, wait_until="domcontentloaded")
            png = path.with_suffix(".png")
            await page.locator("svg").screenshot(path=str(png), animations="disabled")
            with Image.open(png) as original:
                size = (1080, round(original.height * 1080 / original.width))
                frame = original.convert("RGB").resize(size, Image.Resampling.LANCZOS)
                images.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=96))
            if index % 20 == 0:
                print(f"Rendered {index + 1}/{len(frames)} real terminal frames", flush=True)
        await browser.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        output,
        save_all=True,
        append_images=images[1:],
        duration=[duration for _, duration in frames],
        loop=0,
        optimize=True,
        disposal=2,
    )
    images[-1].convert("RGB").save(output.with_name(output.stem + "-poster.png"))
    output.with_name(output.stem + "-demo.json").write_text(json.dumps(report, indent=2) + "\n")
    with Image.open(output) as gif:
        count = gif.n_frames
        duration = sum(gif.seek(i) or gif.info.get("duration", 0) for i in range(count))
    if output.stat().st_size > 8 * 1024 * 1024:
        raise RuntimeError("GIF exceeds the README size budget")
    print(
        json.dumps(
            {
                "gif": str(output),
                "frames": count,
                "duration_ms": duration,
                "bytes": output.stat().st_size,
                "model": report["model"],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--provider")
    parser.add_argument("--output", default="docs/assets/live-bash.gif")
    args = parser.parse_args()
    settings = Settings(args.config)
    if args.provider:
        settings.ai.default_model = args.provider
    settings.ai.max_tokens = min(settings.ai.max_tokens, 768)
    with tempfile.TemporaryDirectory(prefix="aivim-demo-") as temporary:
        frames, report = asyncio.run(capture(settings, Path(temporary)))
        asyncio.run(render(frames, Path(args.output), report))


if __name__ == "__main__":
    main()
