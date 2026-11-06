# Qualification scripts

`python scripts/bump_version.py --validate` checks the version authority, runtime import and VERSION mirror. `patch`, `minor`, `major`, or an explicit PEP 440 version (including alpha/beta/rc prereleases) updates the authority, VERSION mirror and frontend metadata. `--tag` prints the corresponding Git tag. `pyproject.toml` reads the authority dynamically.

`python scripts/check_source.py` parses package, verification, retained test and script sources without executing demos. Run `python -m pytest verification` for behavior and `python -m unittest tests.test_buffer tests.test_history tests.test_utils` for retained support regressions.

Build and check wheel/sdist archives, then run `scripts/installed_smoke.py` in a clean installed-wheel environment from outside source. Follow [docs/RELEASE.md](../docs/RELEASE.md) for platform/provider/native qualification and rollback. No script publishes or deploys this candidate.

`python scripts/record_live_demo.py` captures a real local-model Bash workflow and
exports a GIF with shortened idle inference waits. Install the `demo` extra first.
