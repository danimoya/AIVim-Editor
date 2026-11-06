"""Keep Python, VERSION, and frontend release identities in sync."""

import argparse
import ast
import json
from pathlib import Path
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[1]


def version():
    tree = ast.parse((ROOT / "aivim/_version.py").read_text())
    return next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets)
    )


def tag_for(value):
    parsed = Version(value)
    result = f"v{parsed.major}.{parsed.minor}.{parsed.micro}"
    if parsed.pre:
        label, number = parsed.pre
        result += "-" + {"a": "alpha", "b": "beta", "rc": "rc"}[label] + "." + str(number)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bump", nargs="?")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--tag", action="store_true", help="Print the Git tag for this Python version"
    )
    args = parser.parse_args()
    current = version()
    if args.tag:
        print(tag_for(current))
        return
    if args.validate:
        assert (ROOT / "VERSION").read_text().strip() == current, "VERSION mismatch"
        assert str(Version(current)) == current, "Version must use canonical PEP 440 spelling"
        assert (
            'version = {attr = "aivim._version.__version__"}'
            in (ROOT / "pyproject.toml").read_text()
        )
        assert "from ._version import __version__" in (ROOT / "aivim/__init__.py").read_text()
        if (ROOT / "package.json").exists():
            assert (
                json.loads((ROOT / "package.json").read_text())["version"] == tag_for(current)[1:]
            )
            lock = json.loads((ROOT / "package-lock.json").read_text())
            assert lock["version"] == lock["packages"][""]["version"] == tag_for(current)[1:]
        print("Versions agree:", current, "/", tag_for(current))
        return
    if not args.bump:
        parser.error("Supply major/minor/patch, a PEP 440 version, or --validate")
    if args.bump in ("major", "minor", "patch"):
        parsed = Version(current)
        parts = [parsed.major, parsed.minor, parsed.micro]
        index = ("major", "minor", "patch").index(args.bump)
        parts[index] += 1
        for i in range(index + 1, 3):
            parts[i] = 0
        new = ".".join(map(str, parts))
    else:
        try:
            parsed = Version(args.bump)
            if parsed.local or parsed.post is not None or parsed.dev is not None:
                raise InvalidVersion(args.bump)
            new = str(parsed)
        except InvalidVersion:
            parser.error("Expected a release or alpha/beta/rc version, such as 1.0.0a1")
    (ROOT / "aivim/_version.py").write_text(
        '"""Single release version authority."""\n__version__ = ' + repr(new) + "\n"
    )
    (ROOT / "VERSION").write_text(new + "\n")
    for filename in ("package.json", "package-lock.json"):
        path = ROOT / filename
        if path.exists():
            data = json.loads(path.read_text())
            data["version"] = tag_for(new)[1:]
            if filename == "package-lock.json":
                data["packages"][""]["version"] = tag_for(new)[1:]
            path.write_text(json.dumps(data, indent=2) + "\n")
    print("Prepared", new, "/", tag_for(new))


if __name__ == "__main__":
    main()
