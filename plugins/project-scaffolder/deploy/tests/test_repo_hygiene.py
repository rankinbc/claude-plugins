"""Mechanical enforcement of the structural rules declared in CLAUDE.md.

CLAUDE.md states "No file over ~500 lines" and "outputs land under
output/<component>/". Rules nothing enforces decay, so they are checked here.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MAX_LINES = 500

SOURCE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rs", ".cs", ".rb", ".java", ".ps1",
}

# Skipped wherever they appear: tool caches, dependency trees, VCS metadata.
SKIP_ANYWHERE = {
    ".git", ".hg", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis",
    ".tox", ".nox", ".eggs", "_archive", "migrations", "alembic",
}

# Skipped only at the project root. Names like `data`, `output`, `build` or `env`
# are legitimate source folders inside a component (components/x/build/...), so
# skipping them at any depth would silently exempt real code from the limit.
SKIP_AT_ROOT = {
    "data", "output", "dist", "build", "htmlcov", ".scaffolding", "env", "ENV",
}


def _is_virtualenv(path: Path) -> bool:
    # Catches venvs with any name (`.venv-3.12`, `py311`, ...).
    return (path / "pyvenv.cfg").is_file()


def _source_files() -> list[Path]:
    files: list[Path] = []
    # os.walk with in-place pruning never descends into skipped trees; a
    # rglob-then-filter walk would crawl every file in .venv/node_modules first.
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        current = Path(dirpath)
        at_root = current == PROJECT_ROOT
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_ANYWHERE
            and not d.endswith(".egg-info")
            and not (at_root and d in SKIP_AT_ROOT)
            and not _is_virtualenv(current / d)
        ]
        files.extend(current / f for f in filenames if Path(f).suffix in SOURCE_SUFFIXES)
    return sorted(files)


@pytest.mark.parametrize(
    "source_file",
    _source_files(),
    ids=lambda p: str(p.relative_to(PROJECT_ROOT)).replace("\\", "/"),
)
def test_source_file_under_line_limit(source_file: Path) -> None:
    """Every source file stays under the 500-line limit CLAUDE.md declares."""
    line_count = len(source_file.read_text(encoding="utf-8", errors="replace").splitlines())
    relative = source_file.relative_to(PROJECT_ROOT)
    assert line_count <= MAX_LINES, (
        f"{relative} is {line_count} lines (limit {MAX_LINES}). "
        "Split it by feature; keep a facade module re-exporting the public names "
        "so import paths stay stable."
    )


def test_no_generated_artifacts_at_project_root() -> None:
    """Generated artifacts belong under output/<component>/<date>_<desc>/, never the root."""
    stray = [
        p.name
        for p in PROJECT_ROOT.iterdir()
        if p.is_file() and p.suffix in {".csv", ".xlsx", ".parquet", ".db", ".sqlite", ".log"}
    ]
    assert not stray, (
        f"Generated artifacts at the project root: {stray}. "
        "Move them under output/<component>/<YYYY-MM-DD>_<description>/."
    )
