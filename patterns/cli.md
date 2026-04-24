# Shape: CLI Tool

Command-line utility with subcommands, config, structured output.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/) lives at the project root. The CLI's `pyproject.toml` typically lives at the project root when the CLI is THE main component, or inside the component folder when it coexists with other components.

## Default stack

- **Python 3.11+** + **click** (or **Typer** if user prefers type-hint-driven)
- `pipx install .` for end-user installation
- `pyproject.toml` for packaging

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                   # Purpose / inputs / outputs / how to run
├── src/
│   └── <package_name>/
│       ├── __init__.py
│       ├── __main__.py         # `python -m <package>` entry
│       ├── cli.py              # click root group
│       ├── commands/
│       │   ├── __init__.py
│       │   └── *.py            # One subcommand per file
│       └── utils/
├── tests/
│   ├── conftest.py
│   └── test_*.py
└── pyproject.toml              # Bin declaration + deps (scoped to this component)
```

If the CLI writes files for the user to consume, they go in `output/<component_name>/<YYYY-MM-DD>_<run>/` at the project root. If the CLI reads user-provided inputs, they come from `data/<source_name>/` at the project root (or from paths the user passes on the command line).

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). `requirements.txt` / `pyproject.toml` / `.env.example` are shipped verbatim when called out below — dependencies and secrets structure need to be present for `/execute-prp` to run. The code below is the implementation target `/execute-prp` uses during the build stage.

**`pyproject.toml`** (click-based with bin entry):
```toml
[project]
name = "<cli-name>"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
]

[project.scripts]
<cli-name> = "<package_name>.cli:main"

[tool.pytest.ini_options]
cache_dir = "~/.cache/pytest"

[tool.ruff]
cache-dir = "~/.cache/ruff"
```

**`src/<package>/cli.py`**:
```python
import click
from <package>.commands import scan, apply_

@click.group()
@click.version_option()
def main():
    """<One-line description>."""
    pass

main.add_command(scan.scan)
main.add_command(apply_.apply)
```

**`src/<package>/commands/scan.py`**:
```python
import json
import click

@click.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output")
@click.option("--quiet", is_flag=True, help="Errors only")
def scan(directory: str, as_json: bool, quiet: bool):
    """Inspect <directory> without making changes."""
    results = [{"file": "example.txt", "status": "ok"}]
    if as_json:
        click.echo(json.dumps(results, indent=2))
    elif not quiet:
        for r in results:
            click.echo(f"  {r['status']}: {r['file']}")
```

## How to run

From the project root:

```bash
pipx install components/<component_name>
<cli-name> scan ./some-dir
<cli-name> scan ./some-dir --json
<cli-name> apply ./some-dir --yes
```

During dev: `pip install -e components/<component_name>` and run the same commands.

## Gotchas for CLAUDE.md

- **Destructive actions need --confirm or --yes**: a plain `apply` without a flag should print what it WOULD do and exit non-zero with a reminder.
- **Journal before destructive change**: write a `.journal` file with the before-state BEFORE making changes. Enables `undo`.
- **`--json` output everywhere**: any command that produces results should have a `--json` flag for machine consumption. Human output is fine by default.
- **Progress to stderr, data to stdout**: so users can pipe stdout to files/other commands without progress-noise pollution.
- **Unicode-safe file handling**: test on Linux/Mac/Windows with non-ASCII filenames at least once.
- **No network calls by default**: if the tool needs to hit the network, make it explicit (flag or env var).
- **Permissions errors are non-fatal per file**: log, continue, exit 0 if at least one file was processed; exit 1 only if everything failed.

## Validation

From the project root:

```bash
ruff check components/<component_name>/src/
pytest -q components/<component_name>/tests/
pip install -e components/<component_name>
<cli-name> --help >/dev/null && echo "CLI invokable"
<cli-name> --version
```

## Interview follow-ups

- "What's the tool called? (short, unix-friendly — `media-rename`, not `My Cool Renamer`)"
- "What's the main verb? Is there more than one subcommand?"
- "Does it modify files/system, or is it read-only?"
- "What inputs — file paths, URLs, stdin?"
- "JSON output for scripting, or just human-readable?"
- "Install path — pip/pipx, Homebrew, standalone binary?"
