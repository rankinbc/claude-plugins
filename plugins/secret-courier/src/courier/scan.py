"""Scanner and masker over :mod:`courier.patterns`. Invariant (pinned by tests): ``scan_text(sanitize_text(s)) == []``.

A ``Finding`` carries the rule, the location, the length and a 12-hex digest of the token, never the token.
``main`` is ``courier scan``: files and directories, exit 1 with ``--fail-on-findings``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from courier.patterns import (
    CONN_SECRET_RE,
    KV_SECRET_SRC,
    MASK,
    SECRET_VALUE_PATTERNS,
    URL_USERINFO_RE,
    iter_high_entropy,
    iter_opaque,
)

_CONN_LEAK_RE = re.compile(
    r"(?i)\b(?:password|pwd|accountkey|sharedaccesskey|sharedaccesssignature|instrumentationkey|"
    r"clientsecret|apikey)\s*=\s*(?!<redacted>|\[MASKED\]|\{\{|\$\{|\$\(|#\{|\[!!)[^;\s\"']{6,}"
    "|" + KV_SECRET_SRC
)
_EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build"}
_TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".csv",
    ".log",
    ".ps1",
    ".psm1",
    ".py",
    ".toml",
    ".env",
    ".sql",
    ".cmd",
    ".sh",
    ".ini",
    ".cfg",
    ".xml",
    ".properties",
    ".ts",
    ".js",
}
IGNORE_MARKER = "courier-scan: ignore-file"


@dataclass(frozen=True)
class Finding:
    rule: str
    location: str
    length: int
    digest: str

    def __str__(self) -> str:
        return f"{self.rule} at {self.location} (len={self.length}, sha={self.digest})"


def _digest(tok: str) -> str:
    return hashlib.sha256(tok.encode("utf-8", "replace")).hexdigest()[:12]


def scan_text(text: str, location: str = "<text>") -> list[Finding]:
    if not text:
        return []
    out: list[Finding] = []
    for rule, pat in SECRET_VALUE_PATTERNS:
        for m in pat.finditer(text):
            tok = m.group(0)
            out.append(Finding(rule, location, len(tok), _digest(tok)))
    for m in _CONN_LEAK_RE.finditer(text):
        out.append(Finding("conn_leak", location, len(m.group(0)), _digest(m.group(0))))
    for m in iter_high_entropy(text):
        out.append(Finding("high_entropy", location, len(m.group(0)), _digest(m.group(0))))
    return out


def scan_strict(text: str, location: str = "<text>") -> list[Finding]:
    """``scan_text`` plus the strict prose rule (any long token that does not read as a name)."""
    out = scan_text(text, location)
    out.extend(Finding("opaque", location, len(m.group(0)), _digest(m.group(0))) for m in iter_opaque(text))
    return out


def mask_connection_string(s: str) -> str:
    s = CONN_SECRET_RE.sub(lambda m: f"{m.group(1)}={MASK}", s)
    return URL_USERINFO_RE.sub(lambda m: f"{m.group(1)}{MASK}@", s)


def _shape_sub(m: re.Match[str]) -> str:
    keep = m.groupdict().get("keep")
    return f"{keep}{MASK}" if keep else MASK


def sanitize_text(s: str) -> str:
    """Mask every value shape; idempotent."""
    if not s:
        return s
    s = mask_connection_string(s)
    for _, pat in SECRET_VALUE_PATTERNS:
        s = pat.sub(_shape_sub, s)
    for m in reversed(list(iter_high_entropy(s))):
        s = s[: m.start()] + MASK + s[m.end() :]
    return s


def redact(text: str) -> tuple[str, bool]:
    """``(masked text, anything found)`` for script output: a leak becomes an error upstream."""
    masked = sanitize_text(text or "")
    return masked, bool(scan_text(text or ""))


def scan_file(path: str | Path) -> list[Finding]:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    parts = set(p.parts)
    if "tests" in parts and ("fixtures" in parts or IGNORE_MARKER in text[:2048]):
        return []
    return scan_text(text, str(p))


def scan_paths(paths: list[str | Path]) -> list[Finding]:
    findings: list[Finding] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in p.rglob("*"):
                if any(part in _EXCLUDE_DIRS for part in f.parts):
                    continue
                if f.is_file() and (f.suffix.lower() in _TEXT_SUFFIXES or f.name.startswith(".env")):
                    findings.extend(scan_file(f))
        elif p.is_file():
            findings.extend(scan_file(p))
    return findings


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="courier scan", description="Scan files for secret-shaped values (never prints a value)."
    )
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--fail-on-findings", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    findings = scan_paths(args.paths)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        for f in findings:
            print(str(f))
        print(f"{len(findings)} finding(s)")
    return 1 if (findings and args.fail_on_findings) else 0


__all__ = [
    "IGNORE_MARKER",
    "Finding",
    "main",
    "redact",
    "sanitize_text",
    "scan_file",
    "scan_paths",
    "scan_strict",
    "scan_text",
]

if __name__ == "__main__":
    sys.exit(main())
