# Contributing

Use a scoped checkout and an isolated environment. The active entrypoint is `Editor.handle_input`, with `Display` and `CommandHandler`; legacy `KeyHandler` and `CommandProcessor` remain compatibility code and are not release evidence for that entrypoint.

Install `.[test,build]` and Playwright Chromium. Run `python scripts/check_source.py`, `python scripts/bump_version.py --validate`, `python -m pytest verification`, and `python -m unittest tests.test_buffer tests.test_history tests.test_utils`. The new fixtures instantiate real editor dispatch, use temporary synthetic files, deny external network access and exercise real SDK adapters against loopback providers. Historical mock-based tests remain under `tests` for comparison. Do not replace real dispatch with mocks when testing editor behavior.

Build in a disposable copy and install the resulting wheel into a fresh environment. Run `scripts/installed_smoke.py` from outside the checkout so imports cannot accidentally come from source. See [release qualification](docs/RELEASE.md). CI has no publishing or deployment action. Do not treat a configured model name, a template or a historical coverage number as verified live evidence.
