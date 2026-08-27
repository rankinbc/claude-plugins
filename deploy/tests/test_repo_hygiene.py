"""Mechanical enforcement of the structural rules declared in CLAUDE.md.

CLAUDE.md states "No file over ~500 lines" and "outputs land under
output/<component>/". Rules nothing enforces decay, so they are checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MAX_LINES = 500

SOURCE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rs", ".cs", ".rb", ".java", ".ps1",
}

SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis",
    "data", "output", "dist", "build", "htmlcov", ".scaffolding",
    "_archive", "migrations", "alembic",
}


def _source_files() -> list[Path]:
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(PROJECT_ROOT).parts):
            continue
        files.append(path)
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
