"""The fixed provenance tiers and how to find their tags in Markdown."""
import re

# Strongest first. UNKNOWN is a valid tag but never wins a conflict.
TIERS = ("PRIMARY", "EXPERT", "SECONDARY", "INFERRED", "OBSERVED", "UNKNOWN")
WEAK = ("INFERRED", "OBSERVED")
MAPPED_TIERS = ("PRIMARY", "EXPERT", "SECONDARY")

# [PRIMARY], [UNKNOWN: est 3-5] or [PRIMARY: "exact quote" https://address]. Group 2 is the
# text after the colon, which may wrap across lines. A quote that opens that text may contain
# square brackets; anywhere else a "]" ends the tag. The lookahead skips links like [API](url).
TAG_RE = re.compile(r"\[([A-Z][A-Z_]+)(?::(\s*(?:\"[^\"]*\"|“[^”]*”)?[^\]]*))?\](?!\()")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def fence(line):
    """The character that opens or closes a fenced code block on this line, or None."""
    match = FENCE_RE.match(line)
    return match.group(1)[0] if match else None


def code_spans(text):
    """(start, end) of every fenced block and inline code span. Tags inside them are examples."""
    spans, pos, opened = [], 0, None
    prose = []
    for line in text.splitlines(keepends=True):
        mark = fence(line)
        if opened is None and mark:
            opened = (pos, mark)
        elif opened is not None and mark == opened[1]:
            spans.append((opened[0], pos + len(line)))
            opened = None
        elif opened is None:
            prose.append((pos, line))
        pos += len(line)
    if opened is not None:
        spans.append((opened[0], pos))
    for start, line in prose:
        spans += [(start + m.start(), start + m.end()) for m in INLINE_CODE_RE.finditer(line)]
    return spans


def in_code(spans, index):
    return any(start <= index < end for start, end in spans)


def find_tags(text):
    """Every provenance tag in the text, except those inside code."""
    spans = code_spans(text)
    return [m for m in TAG_RE.finditer(text) if not in_code(spans, m.start())]


def stronger(a, b):
    """Return whichever of two tiers wins a conflict."""
    return a if TIERS.index(a) <= TIERS.index(b) else b


def scan_markdown(text):
    counts = {tier: 0 for tier in TIERS}
    unknown_tags = []
    for match in find_tags(text):
        tag = match.group(1)
        if tag in counts:
            counts[tag] += 1
        elif tag not in unknown_tags:
            unknown_tags.append(tag)
    return {"counts": counts, "unknown_tags": unknown_tags}
