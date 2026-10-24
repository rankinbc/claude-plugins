"""Check every PRIMARY claim against the source it cites.

A researcher reads the web through tools that return a model's summary, so a
"quote" can be a sentence the page never contained. The script therefore opens
each cited source itself and looks for the quoted words. A claim whose quote
is not there, or that gives nothing to check, is downgraded to SECONDARY with
the reason recorded.

A source that cannot be reached this time (a timeout, a dropped connection, a
server error, or this run's time for fetching used up) proves nothing either
way. Its claim is left as it is, counted as unchecked, and checked again on
the next run. Its file does not count as checked until then.

After `sweep`, every PRIMARY left in the knowledge base has been confirmed,
except those in files the result reports as unchecked.
"""
import concurrent.futures
import hashlib
import html
import http.client
import ipaddress
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .provenance import TAG_RE, find_tags
from .store import RRError, read_json, read_text, write_json, write_text

MIN_QUOTE = 20          # normalized characters; anything shorter could match by accident
MAX_BYTES = 5_000_000   # the most read from one page or local file
TIMEOUT = 15            # seconds for one page: connecting and downloading together
BUDGET = 60             # seconds of fetching per run; Claude Code stops a command after 120
WORKERS = 6             # pages fetched at once
ALLOW_PRIVATE = False   # tests set this to reach a server on this machine
LEDGER = "verification.json"
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
QUOTE_RE = re.compile(r"[\"“](.+)[\"”]", re.DOTALL)
_TYPOGRAPHY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                             "–": "-", "—": "-", " ": " "})
NO_QUOTE = "no quote given"
OUT_OF_TIME = "not fetched: this run's time for fetching was used up"
# short forms, safe to write inside a Markdown tag
SHORT = (("not found", "quote not found in source"), ("too short", "quote too short to check"),
         ("no quote", NO_QUOTE), ("no source", "no source given"),
         ("could not be fetched", "source unreachable"), ("could not be read", "source unreadable"),
         ("was refused", "source address refused"), ("cite itself", "source is the knowledge base itself"),
         ("does not contain", "quote does not contain the value"))
# failures about the source, not the quote: a rewritten tag keeps the quote and address
KEEP_EVIDENCE = ("could not be fetched", "could not be read", "was refused", "cite itself")


class Pending(str):
    """Why a claim could not be checked this time. It is checked again on the next run."""


class Refused(Exception):
    """An address the script will not open: not http(s), or a private, local or reserved host."""


def normalize(text):
    """Reduce text to what a quote must match: no markup, plain quotes, single spaces, one case."""
    text = re.sub(r"<[^>]+>", " ", html.unescape(text))
    return re.sub(r"\s+", " ", text.translate(_TYPOGRAPHY)).strip().lower()


NUMBER_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([km])?\b", re.IGNORECASE)


def _states(quote, value):
    """True if the quote contains this number, however it is written: 150000, 150,000 or 150K."""
    for digits, scale in NUMBER_RE.findall(quote):
        try:
            number = float(digits.replace(",", ""))
        except ValueError:
            continue
        number *= {"k": 1_000, "m": 1_000_000}.get(scale.lower(), 1)
        if abs(number - value) < 1e-9:
            return True
    return False


# ---- fetching: http(s) only, public hosts only, bounded in size and time


def _check_ip(address, host):
    ip = ipaddress.ip_address(address.split("%")[0])
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if not ip.is_global or ip.is_multicast:
        raise Refused(f"{host} is a private, local or reserved address")


def check_address(url):
    """Raise Refused unless this is an http(s) address whose host is on the public internet."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise Refused(f"only http and https addresses are opened, not {parts.scheme or 'none'}")
    try:
        host, port = parts.hostname, parts.port
    except ValueError:
        raise Refused("the address has an invalid port") from None
    if not host:
        raise Refused("the address has no host")
    if ALLOW_PRIVATE:
        return
    try:
        infos = socket.getaddrinfo(host, port or (443 if parts.scheme.lower() == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as e:
        raise urllib.error.URLError(e) from None  # a lookup can fail for a while; try again later
    for info in infos:
        _check_ip(info[4][0], host)


def _proxy_hosts():
    return {urllib.parse.urlsplit(p).hostname for p in urllib.request.getproxies().values()}


def _guarded_connection(address, *args, **kwargs):
    """Connect, then check the address actually reached, so a second DNS answer cannot slip through."""
    sock = socket.create_connection(address, *args, **kwargs)
    if not ALLOW_PRIVATE and address[0] not in _proxy_hosts():
        try:
            _check_ip(sock.getpeername()[0], address[0])
        except Refused:
            sock.close()
            raise
    return sock


class _HTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _guarded_connection


class _HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _guarded_connection


class _HTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_HTTPConnection, req)


class _HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_HTTPSConnection, req, context=self._context)


class _Redirects(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        # checked before urllib's own scheme check, which would report a refusal as an HTTP error
        location = headers.get("location") or headers.get("uri")
        if location:
            check_address(urllib.parse.urljoin(req.full_url, location))
        return super().http_error_302(req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_address(urllib.parse.urljoin(req.full_url, newurl))  # every hop, not only the first
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener():
    # built by hand so there is no file:, ftp: or data: handler to fall back on
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.ProxyHandler(), urllib.request.UnknownHandler(), _HTTPHandler(),
                    _HTTPSHandler(), urllib.request.HTTPDefaultErrorHandler(), _Redirects(),
                    urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    return opener


def decode(data, charset):
    """Bytes to text. A charset Python does not know falls back to UTF-8."""
    try:
        return data.decode(charset or "utf-8", "replace")
    except LookupError:
        return data.decode("utf-8", "replace")


def _http_get(url):
    check_address(url)
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "recursive-research quote check"})
    chunks, size = [], 0
    with _opener().open(request, timeout=TIMEOUT) as response:
        while size < MAX_BYTES:
            # the socket timeout covers each read; this covers a page that trickles in
            if time.monotonic() - started > TIMEOUT:
                raise TimeoutError(f"the page took more than {TIMEOUT} seconds")
            chunk = response.read(min(65536, MAX_BYTES - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        charset = response.headers.get_content_charset()
    return decode(b"".join(chunks), charset)


FETCH = _http_get  # replaced in tests

# One run is one command. It gets BUDGET seconds of fetching, and an address that failed
# in it is not tried again until the next run.
_run = {"deadline": None, "failed": {}}


def reset_run():
    _run["deadline"] = None
    _run["failed"] = {}


def _remaining():
    if _run["deadline"] is None:
        _run["deadline"] = time.monotonic() + BUDGET
    return _run["deadline"] - time.monotonic()


def _attempt(url):
    """Fetch one address. Returns (text, problem, keep): keep means the outcome is worth saving."""
    try:
        return FETCH(url), None, True
    except Refused as e:
        return None, f"the source address was refused: {e}", False
    except Exception as e:  # any network, TLS or decoding failure means "could not check"
        message = f"{type(e).__name__}: {e}"[:200]
        if isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code not in (408, 425, 429):
            return None, f"the source could not be fetched: {message}", True  # gone or forbidden
        return None, Pending(f"the source could not be reached this time: {message}"), False


def _index_path(ws):
    return Path(ws) / "sources" / "index.json"


def _load_index(ws):
    path = _index_path(ws)
    return read_json(path) if path.is_file() else {}


def _settled(entry):
    # an error saved by an older version, without "lasting", may have been passing: retry it
    return bool(entry) and bool(entry.get("file") or entry.get("lasting"))


def _record(ws, index, url, outcome):
    text, problem, keep = outcome
    if not keep:
        _run["failed"][url] = problem
    elif problem is None:
        name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] + ".txt"
        write_text(Path(ws) / "sources" / name, text)
        index[url] = {"file": name, "error": None}
    else:
        index[url] = {"file": None, "error": problem, "lasting": True}


def _prefetch(ws, urls):
    """Fetch the addresses not yet on disk, several at once, within this run's time."""
    index = _load_index(ws)
    todo = sorted({u for u in urls if not _settled(index.get(u)) and u not in _run["failed"]})
    if not todo:
        return
    if _remaining() <= 0:
        _run["failed"].update((u, Pending(OUT_OF_TIME)) for u in todo)
        return
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=min(WORKERS, len(todo)))
    futures = {pool.submit(_attempt, url): url for url in todo}
    done, late = concurrent.futures.wait(futures, timeout=max(0.0, _remaining()))
    pool.shutdown(wait=False)
    for future in late:
        future.cancel()
        _run["failed"][futures[future]] = Pending(OUT_OF_TIME)
    for future in done:
        _record(ws, index, futures[future], future.result())
    write_json(_index_path(ws), index)


def _fetch_cached(ws, url):
    """Return (text, problem). A page, or a lasting failure, is fetched once per workspace."""
    index = _load_index(ws)
    entry = index.get(url)
    if not _settled(entry) and url not in _run["failed"]:
        if _remaining() <= 0:
            return None, Pending(OUT_OF_TIME)
        _record(ws, index, url, _attempt(url))
        write_json(_index_path(ws), index)
        entry = index.get(url)
    if url in _run["failed"]:
        return None, _run["failed"][url]
    if entry["error"]:
        error = entry["error"]
        # older versions saved the bare error
        return None, error if error.startswith("the source") else f"the source could not be fetched: {error}"
    return read_text(Path(ws) / "sources" / entry["file"]), None


# ---- local files


def _research(ws):
    """The research folder that holds every subject's workspace."""
    return Path(ws).resolve().parent


def _read_local(ws, path):
    """Return (text, problem) for a source_file."""
    resolved = Path(path).resolve()
    research = _research(ws)
    if resolved == research or research in resolved.parents:
        return None, ("the source file is inside the research folder, and the knowledge base "
                      "cannot cite itself")
    if not resolved.is_file():
        return None, "the source file could not be read: it is not a regular file"
    if resolved.stat().st_size > MAX_BYTES:
        return None, f"the source file could not be read: it is larger than {MAX_BYTES} bytes"
    try:
        return read_text(resolved), None
    except (RRError, OSError) as e:
        return None, f"the source file could not be read: {e}"


def _locate(ws, claim):
    """Where the script can read this claim's source: ('file', path), ('url', url) or None.

    A relative source_file is read from the folder that holds the research folder, which is
    the project folder when the script runs with `--root research`.
    """
    local = claim.get("source_file")
    if isinstance(local, str) and local.strip():
        given = Path(local.strip())
        for candidate in ((given,) if given.is_absolute() else (_research(ws).parent / given, Path(ws) / given)):
            if candidate.exists():
                return "file", candidate
    url = claim.get("source_url")
    if isinstance(url, str) and url.strip().lower().startswith(("http://", "https://")):
        return "url", url.strip()
    match = URL_RE.search(str(claim.get("source", "")))
    if match:
        return "url", match.group(0).rstrip(".,;")
    return None


def check(ws, claim):
    """Why this claim's quote cannot be confirmed, or None if it is in the source.

    `claim` is any mapping with `quote` and one of `source_url`, `source_file`,
    or a web address inside `source`. A Pending reason means the source was not
    reached this time and the claim should be checked again later.
    """
    if not str(claim.get("quote", "")).strip():
        return NO_QUOTE
    quote = normalize(str(claim["quote"]))
    if len(quote) < MIN_QUOTE:
        return f"the quote is too short to check (under {MIN_QUOTE} characters)"
    where = _locate(ws, claim)
    if where is None:
        return ("no source the script can open was given; "
                "it needs source_url, a web address in source, or source_file")
    if where[0] == "file":
        text, problem = _read_local(ws, where[1])
    else:
        text, problem = _fetch_cached(ws, where[1])
    if problem:
        return problem
    if quote not in normalize(text):
        return "the quote was not found in the cited source"
    return None


def _short(problem):
    return next((short for needle, short in SHORT if needle in problem), "not confirmed")


def _counts():
    return {"verified": 0, "downgraded": 0, "unchecked": 0}


def _settle(ws, record, key):
    """Verify one record whose tier lives under `key`. Returns 'verified', 'downgraded', 'unchecked' or None."""
    # a record downgraded on an earlier run is checked again, so the result is repeatable
    if record.get(key) != "PRIMARY" and record.get("downgraded_from") != "PRIMARY":
        return None
    problem = check(ws, record)
    if problem is None:
        record[key] = "PRIMARY"
        record["verified"] = True
        record.pop("downgraded_from", None)
        record.pop("verify_note", None)
        return "verified"
    if isinstance(problem, Pending):
        if record.get(key) == "PRIMARY":  # left as it is until the source can be reached
            record["verified"] = False
            record["verify_note"] = str(problem)
        return "unchecked"
    record[key] = "SECONDARY"
    record["downgraded_from"] = "PRIMARY"
    record["verified"] = False
    record["verify_note"] = problem
    return "downgraded"


def _quoted(node, found):
    """Every mapping under `node` that carries a quote."""
    if isinstance(node, dict):
        if "quote" in node:
            found.append(node)
        for value in node.values():
            _quoted(value, found)
    elif isinstance(node, list):
        for value in node:
            _quoted(value, found)


def _urls(ws, path):
    """The web addresses that checking this file would open."""
    path = Path(path)
    if path.suffix == ".md":
        claims = [_tag_claim(m.group(2) or "") for m in find_tags(read_text(path)) if m.group(1) == "PRIMARY"]
    else:
        claims = []
        _quoted(read_json(path), claims)
    urls = []
    for claim in claims:
        where = _locate(ws, claim)
        if where and where[0] == "url":
            urls.append(where[1])
    return urls


def verify_result(ws, session, task_id):
    """Verify the PRIMARY findings of one stage 4 research result, rewriting the file."""
    path = Path(ws) / "sessions" / session / "raw" / f"{task_id}.json"
    _prefetch(ws, _urls(ws, path))
    doc = read_json(path)
    counts = _counts()
    notes = []
    for index, finding in enumerate(doc.get("findings", [])):
        if not isinstance(finding, dict):
            continue
        outcome = _settle(ws, finding, "tier")
        if outcome:
            counts[outcome] += 1
        if outcome == "downgraded":
            notes.append({"finding": index, "note": finding["verify_note"]})
    write_json(path, doc)
    return {"task": task_id, **counts, "notes": notes}


def _walk(ws, node, counts):
    if isinstance(node, dict):
        if "tier" in node:
            outcome = _settle(ws, node, "tier")
            if outcome:
                counts[outcome] += 1
        meta = node.get("_meta")
        if isinstance(meta, dict):
            outcome = _settle(ws, meta, "provenance")
            if outcome:
                counts[outcome] += 1
        for key, value in node.items():
            if key != "_meta":
                _walk(ws, value, counts)
    elif isinstance(node, list):
        for value in node:
            _walk(ws, value, counts)


def verify_json(ws, path):
    """Verify a JSON leaf: its `_meta` block and any entry that carries its own `tier`."""
    _prefetch(ws, _urls(ws, path))
    doc = read_json(path)
    counts = _counts()
    _walk(ws, doc, counts)
    write_json(path, doc)
    return counts


def _tag_claim(payload):
    """Read `"exact quote" address` from inside a Markdown tag."""
    match = QUOTE_RE.search(payload)
    if not match:
        return {}
    rest = payload[match.end():].strip()
    url = URL_RE.search(rest)
    claim = {"quote": match.group(1)}
    if url:
        claim["source_url"] = url.group(0).rstrip(".,;")
    elif rest:
        claim["source_file"] = rest
    return claim


def verify_markdown(ws, path):
    """Verify every `[PRIMARY: "quote" address]` tag in a Markdown file, rewriting failures.

    Tags inside code are examples, not claims, and are left alone. A tag whose source was
    not reached this time is left exactly as it is. A tag whose source could not be used
    keeps its quote and address: `[SECONDARY: "quote" address; was PRIMARY, source unreachable]`.
    """
    _prefetch(ws, _urls(ws, path))
    counts = _counts()
    text = read_text(path)
    claims = {m.start() for m in find_tags(text)}

    def settle(match):
        if match.group(1) != "PRIMARY" or match.start() not in claims:
            return match.group(0)
        payload = (match.group(2) or "").strip()
        problem = check(ws, _tag_claim(payload))
        if problem is None:
            counts["verified"] += 1
            return match.group(0)
        if isinstance(problem, Pending):
            counts["unchecked"] += 1
            return match.group(0)
        counts["downgraded"] += 1
        if any(needle in problem for needle in KEEP_EVIDENCE):
            return f"[SECONDARY: {payload}; was PRIMARY, {_short(problem)}]"
        return f"[SECONDARY: was PRIMARY, {_short(problem)}]"

    checked = TAG_RE.sub(settle, text)
    if checked != text:
        write_text(path, checked)
    return counts


def verify_roster(ws, path):
    """Verify an entity roster. Each PRIMARY value needs evidence: a quote and where it is."""
    _prefetch(ws, _urls(ws, path))
    doc = read_json(path)
    counts = _counts()
    for entity in doc.get("entities", []):
        if not isinstance(entity, dict) or not isinstance(entity.get("properties"), dict):
            continue
        properties = entity["properties"]
        given = entity.get("provenance")
        tiers = {name: given if isinstance(given, str) else (given or {}).get(name) for name in properties}
        evidence = entity.get("evidence") if isinstance(entity.get("evidence"), dict) else {}
        old = entity.get("verify_notes") if isinstance(entity.get("verify_notes"), dict) else {}
        notes = {name: note for name, note in old.items() if tiers.get(name) != "PRIMARY"}
        downgraded, waiting = False, set()
        for name, tier in tiers.items():
            if tier != "PRIMARY":
                continue
            claim = evidence.get(name) if isinstance(evidence.get(name), dict) else evidence
            problem = check(ws, claim) if "quote" in claim else NO_QUOTE
            value = properties[name]
            if (problem is None and isinstance(value, (int, float)) and not isinstance(value, bool)
                    and not _states(str(claim["quote"]), value)):
                problem = "the quote does not contain the value"
            if isinstance(problem, Pending):
                notes[name] = str(problem)  # stays PRIMARY, unconfirmed, until the next run
                waiting.add(name)
                counts["unchecked"] += 1
            elif problem:
                tiers[name] = "SECONDARY"
                notes[name] = problem
                downgraded = True
                counts["downgraded"] += 1
            else:
                counts["verified"] += 1
        if downgraded:
            entity["provenance"] = tiers
        if notes:
            entity["verify_notes"] = notes
        else:
            entity.pop("verify_notes", None)
        entity["verified"] = sorted(name for name, tier in tiers.items() if tier == "PRIMARY" and name not in waiting)
    write_json(path, doc)
    return counts


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _targets(ws):
    knowledge = Path(ws) / "knowledge"
    files = [knowledge / "spec.md"]
    files += sorted((knowledge / "tree").rglob("*.md")) + sorted((knowledge / "tree").rglob("*.json"))
    files += sorted((knowledge / "entities").glob("*.json"))
    return [f for f in files if f.is_file()]


def sweep(ws):
    """Verify everything in knowledge/ that has changed since it was last checked.

    A file with claims left unchecked is checked again on the next sweep even if unchanged.
    """
    ws = Path(ws)
    ledger_path = ws / "knowledge" / LEDGER
    files = read_json(ledger_path).get("files", {}) if ledger_path.is_file() else {}
    result = {"files_checked": 0, **_counts()}
    current = {}
    due = []
    for path in _targets(ws):
        rel = path.relative_to(ws).as_posix()
        record = files.get(rel)
        if record and record.get("hash") == _digest(path) and not record.get("unchecked"):
            current[rel] = record
            continue
        due.append((path, rel))
    _prefetch(ws, [url for path, _ in due for url in _urls(ws, path)])
    for path, rel in due:
        if path.suffix == ".md":
            counts = verify_markdown(ws, path)
        elif path.parent.name == "entities":
            counts = verify_roster(ws, path)
        else:
            counts = verify_json(ws, path)
        current[rel] = {"hash": _digest(path), **counts}
        result["files_checked"] += 1
        for key in counts:
            result[key] += counts[key]
    if current != files or not ledger_path.is_file():
        write_json(ledger_path, {"files": current})
    if result["unchecked"]:
        result["next"] = ("some sources could not be reached this time; "
                          "run verify again later to check those claims")
    return result


def is_checked(ws, path):
    """True if this knowledge file is unchanged since a sweep checked every claim in it."""
    ws, path = Path(ws), Path(path)
    ledger_path = ws / "knowledge" / LEDGER
    if not ledger_path.is_file() or not path.is_file():
        return False
    record = read_json(ledger_path).get("files", {}).get(path.relative_to(ws).as_posix())
    return bool(record) and record.get("hash") == _digest(path) and not record.get("unchecked")


def record_for(ws, path):
    """The ledger entry for a knowledge file, or None."""
    ledger_path = Path(ws) / "knowledge" / LEDGER
    if not ledger_path.is_file():
        return None
    return read_json(ledger_path).get("files", {}).get(Path(path).relative_to(ws).as_posix())
