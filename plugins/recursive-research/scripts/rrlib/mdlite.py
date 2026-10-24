"""A small Markdown renderer for the report. Standard library only.

It covers what the knowledge base uses: headings, paragraphs, lists with
checkboxes, tables, code, links and emphasis. Everything is escaped, because
the text was gathered from the web. Provenance tags become badges.
"""
import html
import re

from .provenance import TAG_RE, TIERS, fence

LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"`([^`\n]+)`")
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
QUOTE_RE = re.compile(r"[\"“](.+)[\"”]", re.DOTALL)
ITEM_RE = re.compile(r"^\s*(?:[-*+]|(\d+)[.)])\s+(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
TABLE_RULE_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
REL = 'rel="noopener noreferrer"'
PLACEHOLDER_RE = re.compile(r"\x00(\d+)\x00")


def esc(text):
    return html.escape(str(text), quote=True)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def badge(tier, checked=True, quote=None, url=None, note=None):
    """A provenance badge. PRIMARY shows as verified only when its file has been checked."""
    css = f"tier t-{tier.lower()}"
    if tier == "PRIMARY":
        if not checked:
            return f'<span class="{css} unchecked" title="not yet checked against its source">PRIMARY</span>'
        title = f' title="“{esc(quote)}”"' if quote else ""
        if url and url.lower().startswith(("http://", "https://")):
            return f'<a class="{css} verified" href="{esc(url)}" {REL}{title}>PRIMARY ✓</a>'
        return f'<span class="{css} verified"{title}>PRIMARY ✓</span>'
    title = f' title="{esc(note)}"' if note else ""
    return f'<span class="{css}"{title}>{tier}</span>'


def _tag(tier, payload, checked):
    payload = (payload or "").strip()
    if tier not in TIERS:
        return None
    if tier != "PRIMARY":
        return badge(tier, note=payload or None)
    quote = QUOTE_RE.search(payload)
    url = URL_RE.search(payload[quote.end():]) if quote else None
    return badge(tier, checked, quote.group(1) if quote else None, url.group(0).rstrip(".,;") if url else None)


def inline(text, checked=True, resolve=None):
    """Render one run of text. Code, tags and links are set aside first, then the rest is escaped.

    `resolve` maps a link to another file onto the id of the place the page shows it, or None.
    """
    kept = []  # (rendered HTML, the source text it replaced)
    # the placeholders are NUL-delimited, so a NUL in the input must not survive to look like one
    text = text.replace("\x00", "\ufffd")

    def keep(rendered, source):
        kept.append((rendered, source))
        return f"\x00{len(kept) - 1}\x00"

    def expand(s, which):
        # a kept piece can hold earlier placeholders, such as code inside a link label
        return PLACEHOLDER_RE.sub(lambda m: expand(kept[int(m.group(1))][which], which), s)

    def plain(s):
        return expand(s, 1)

    text = CODE_RE.sub(lambda m: keep(f"<code>{esc(m.group(1))}</code>", m.group(0)), text)

    def tag(match):
        rendered = _tag(match.group(1), plain(match.group(2) or ""), checked)
        return keep(rendered, match.group(0)) if rendered else match.group(0)

    text = TAG_RE.sub(tag, text)

    def link(match):
        label, target = match.group(1), plain(match.group(2))
        if target.lower().startswith(("http://", "https://")):
            return keep(f'<a href="{esc(target)}" {REL}>{esc(label)}</a>', match.group(0))
        anchor = resolve(target) if resolve else None
        if anchor:
            return keep(f'<a href="#{esc(anchor)}">{esc(label)}</a>', match.group(0))
        return label  # a link to a file the page does not show: keep the words, drop the path

    text = LINK_RE.sub(link, text)
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"\bCONFLICT\b", '<span class="conflict">CONFLICT</span>', text)
    return expand(text, 0)


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def render(text, checked=True, heading_offset=0, id_prefix="", resolve=None):
    """Render Markdown to HTML. `checked` says whether this file's PRIMARY tags are verified."""
    lines = text.replace("\r\n", "\n").split("\n")
    out = []
    i, n = 0, len(lines)

    def run(s):
        return inline(s, checked, resolve)

    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        mark = fence(line)
        if mark:
            i += 1
            block = []
            while i < n and fence(lines[i]) != mark:
                block.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre><code>{esc(chr(10).join(block))}</code></pre>")
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = min(6, len(heading.group(1)) + heading_offset)
            title = heading.group(2)
            plain = re.sub(r"<[^>]+>", "", run(title))
            attr = f' id="{esc(id_prefix + slug(html.unescape(plain)))}"' if level - heading_offset > 1 else ""
            out.append(f"<h{level}{attr}>{run(title)}</h{level}>")
            i += 1
            continue

        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        if "|" in line and i + 1 < n and TABLE_RULE_RE.match(lines[i + 1]):
            head = _cells(line)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_cells(lines[i]))
                i += 1
            thead = "".join(f"<th>{run(c)}</th>" for c in head)
            body = "".join("<tr>" + "".join(f"<td>{run(c)}</td>" for c in row) + "</tr>" for row in rows)
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>")
            continue

        item = ITEM_RE.match(line)
        if item:
            ordered = item.group(1) is not None
            items = []
            while i < n:
                m = ITEM_RE.match(lines[i])
                if m and (m.group(1) is not None) == ordered:
                    items.append(m.group(2))
                elif lines[i].strip() and lines[i][:1] in " \t" and items:
                    items[-1] += " " + lines[i].strip()  # a wrapped line of the same item
                else:
                    break
                i += 1
            rendered = []
            for content in items:
                box = re.match(r"\[([ xX])\]\s+(.*)$", content, re.DOTALL)
                if box and box.group(1) == " ":
                    rendered.append(f'<li class="open"><span class="box"></span>{run(box.group(2))}</li>')
                elif box:
                    rendered.append(f'<li class="done"><span class="box">✓</span>{run(box.group(2))}</li>')
                else:
                    rendered.append(f"<li>{run(content)}</li>")
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>{''.join(rendered)}</{tag}>")
            continue

        if line.startswith(("    ", "\t")):
            block = []
            while i < n and (lines[i].startswith(("    ", "\t")) or not lines[i].strip()):
                block.append(lines[i][4:] if lines[i].startswith("    ") else lines[i].lstrip("\t"))
                i += 1
            while block and not block[-1].strip():
                block.pop()
            out.append(f"<pre><code>{esc(chr(10).join(block))}</code></pre>")
            continue

        if line.lstrip().startswith(">"):
            block = []
            while i < n and lines[i].lstrip().startswith(">"):
                block.append(lines[i].lstrip()[1:].strip())
                i += 1
            out.append(f"<blockquote><p>{run(' '.join(block))}</p></blockquote>")
            continue

        block = []
        while i < n and lines[i].strip():
            nxt = lines[i]
            if block and (HEADING_RE.match(nxt) or ITEM_RE.match(nxt) or fence(nxt)
                          or ("|" in nxt and i + 1 < n and TABLE_RULE_RE.match(lines[i + 1]))):
                break
            block.append(nxt.strip())
            i += 1
        out.append(f"<p>{run(' '.join(block))}</p>")
    return "\n".join(out)
