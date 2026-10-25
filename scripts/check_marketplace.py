"""Check that the marketplace and every plugin in it are consistent.

Run from anywhere: python scripts/check_marketplace.py [--tag <plugin>--vX.Y.Z]

- every tracked .json file parses
- each marketplace entry points at a folder whose plugin.json has the same name
- each plugin has a semantic version, a description, README.md, LICENSE and CHANGELOG.md
- each plugin's homepage and repository point at its folder in this repository
- no plugin carries its own marketplace.json
- a plugin hosted in another GitHub repository is pinned to the tag v<version> of the version it lists
- with --tag, the tag names a listed plugin and matches its version
Standard library only. Exits 1 and lists every problem it finds.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/rankinbc/claude-plugins"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
TAG = re.compile(r"^(?P<plugin>[a-z0-9-]+)--v(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$")
REQUIRED_FILES = ("README.md", "LICENSE", "CHANGELOG.md")
GITHUB_REPO = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")


def tracked_json_files():
    out = subprocess.run(["git", "ls-files", "*.json"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / line for line in out.stdout.splitlines() if line]


def check_external(entry, problems):
    """An entry whose source is another GitHub repository; its files are checked in that repository's own CI."""
    name, source = entry.get("name", "?"), entry["source"]
    if source.get("source") != "github" or not GITHUB_REPO.match(source.get("repo", "")):
        problems.append(f"{name}: an external source must be {{\"source\": \"github\", \"repo\": \"owner/name\"}}")
    version = entry.get("version", "")
    if not SEMVER.match(version):
        problems.append(f"{name}: an external entry needs a semantic version, got {version!r}")
    elif source.get("ref") != f"v{version}":
        problems.append(f"{name}: ref should be the release tag v{version}, got {source.get('ref')!r}")
    if not entry.get("description"):
        problems.append(f"{name}: an external entry needs its own description")
    return version


def check(tag=None):
    problems = []
    for path in tracked_json_files():
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{path.relative_to(ROOT)}: not valid JSON ({e})")

    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    versions = {}
    external = set()
    for entry in marketplace.get("plugins", []):
        name = entry.get("name", "?")
        if name in versions:
            problems.append(f"{name}: listed twice in marketplace.json")
        if isinstance(entry.get("source"), dict):
            check_external(entry, problems)
            external.add(name)
            versions[name] = entry.get("version", "")
            continue
        folder = (ROOT / entry.get("source", "")).resolve()
        manifest_path = folder / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            problems.append(f"{name}: {entry.get('source')} has no .claude-plugin/plugin.json")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        where = folder.relative_to(ROOT).as_posix()
        if manifest.get("name") != name:
            problems.append(f"{name}: plugin.json is named {manifest.get('name')!r}")
        version = manifest.get("version", "")
        if not SEMVER.match(version):
            problems.append(f"{name}: version {version!r} is not semantic")
        versions[name] = version
        if not manifest.get("description"):
            problems.append(f"{name}: plugin.json has no description")
        for field in ("homepage", "repository"):
            expected = f"{REPO_URL}/tree/main/{where}"
            if manifest.get(field) != expected:
                problems.append(f"{name}: {field} should be {expected}")
        for required in REQUIRED_FILES:
            if not (folder / required).is_file():
                problems.append(f"{name}: missing {where}/{required}")
        if (folder / ".claude-plugin" / "marketplace.json").exists():
            problems.append(f"{name}: has its own marketplace.json; the root one lists it")
        changelog = folder / "CHANGELOG.md"
        if changelog.is_file() and f"## {version}" not in changelog.read_text(encoding="utf-8"):
            problems.append(f"{name}: CHANGELOG.md has no '## {version}' section")

    if tag:
        match = TAG.match(tag)
        if not match:
            problems.append(f"tag {tag!r} is not <plugin>--vX.Y.Z")
        elif match["plugin"] not in versions:
            problems.append(f"tag {tag!r} names a plugin that is not in the marketplace")
        elif match["plugin"] in external:
            problems.append(f"tag {tag!r} names {match['plugin']}, which is released from its own repository")
        elif versions[match["plugin"]] != match["version"]:
            problems.append(f"tag {tag!r} does not match {match['plugin']} version {versions[match['plugin']]}")
    return problems, versions


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="a release tag to check against the plugin versions")
    args = parser.parse_args()
    problems, versions = check(args.tag)
    for name, version in versions.items():
        print(f"{name} {version}")
    for problem in problems:
        print(f"PROBLEM {problem}")
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
