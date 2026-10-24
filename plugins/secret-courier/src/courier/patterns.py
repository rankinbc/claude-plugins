"""Secret-shaped value detection: one list of rules shared by the scanner (``scan.scan_text``) and the masker
(``scan.sanitize_text``), so anything the scanner can see the masker removes.

Asymmetry rule: a false positive costs one masked value; a false negative costs a credential rotation. Tune
toward masking. Documented trade-off: the entropy catch-all skips pure hex tokens and short low-class tokens
(git SHAs, GUIDs, content hashes are identifiers, not values); a bare 32/64-hex API key with no key name and no
``k=v`` context is therefore not flagged on shape alone.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from itertools import pairwise

MASK = "<redacted>"

# --- key names ---------------------------------------------------------------------------------------------

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[:.\-/\[\]\s]+")


def normalize_key(key: str) -> str:
    """``Auth:ClientSecret`` -> ``auth_client_secret``; ``DB__Password`` -> ``db_password``."""
    k = _CAMEL_BOUNDARY.sub("_", key)
    k = _SEPARATORS.sub("_", k)
    return re.sub(r"_+", "_", k).strip("_").lower()


_SECRET_NAME_TOKENS = (
    r"password|passwd|pwd|passphrase|passcode|secret|secrets|token|tokens|pat|bearer|"
    r"api_?key|account_?key|subscription_?key|shared_?access_?key|shared_?access_?signature|sas|sas_?token|"
    r"private_?key|signing_?key|encryption_?key|master_?key|auth_?key|secret_?key|license_?key|"
    r"client_?secret|app_?secret|connection_?strings?|connstr|conn_?str|instrumentation_?key|"
    r"credential|credentials|authorization|auth|pfx|keystore|cert_?password|security_?code|salt|pepper"
)
SECRET_NAME_RE = re.compile(rf"(?:^|_)(?:{_SECRET_NAME_TOKENS})(?:_|$)|(?:^|_)key$")
NON_SECRET_SUFFIX_RE = re.compile(
    r"(?:^|_)(?:name|names|uri|url|endpoint|enabled|enable|disabled|expir\w*|lifetime|ttl|timeout|"
    r"minutes|seconds|hours|days|length|min_length|max_length|count|path|version|type|kind|id|"
    r"identifier|provider|source|prefix|suffix|header|header_name|env|env_var|variable|required|"
    r"policy|scope|scopes|audience|issuer|authority|algorithm|format|mode|option|options|setting|"
    r"settings|section|file|filename|cache|interval|vault|vault_name)$"
)


def is_secret_name(key: str) -> bool:
    n = normalize_key(key)
    return bool(SECRET_NAME_RE.search(n)) and not NON_SECRET_SUFFIX_RE.search(n)


# --- connection strings, URLs, placeholders -------------------------------------------------------------------

_NOT_PLACEHOLDER = r"(?!<redacted>|\[MASKED\]|\{\{|\$\{|\$\(|#\{|\[!!)"
CONN_SECRET_RE = re.compile(
    r"(?i)(?<![a-z0-9])("
    r"password|pwd|user\s*id|userid|user\s*name|username|uid|user|"
    r"account\s*key|accountkey|shared\s*access\s*key|sharedaccesskey|"
    r"shared\s*access\s*signature|sharedaccesssignature|"
    r"primary\s*key|primarykey|secondary\s*key|secondarykey|auth\s*key|authkey|access\s*key|accesskey|"
    r"token|api\s*key|apikey|secret|client\s*secret|clientsecret|credential|"
    r"instrumentation\s*key|instrumentationkey"
    r")(\s*=\s*)" + _NOT_PLACEHOLDER + r"([^;]*)"
)
URL_USERINFO_RE = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)" + _NOT_PLACEHOLDER + r"([^/\s@:]+)(:[^/\s@]*)?@")
PLACEHOLDER_RE = re.compile(
    r"^(?:<redacted>|\[[A-Z_ !]+\]|\$\{[^}]*\}|\$\([^)]*\)|#\{[^}]*\}#|\{\{[^}]*\}\}|\*{3,}|x{6,}|"
    r"your[-_ ]?[a-z0-9-]+|changeme|placeholder|todo|tbd|n/?a|none|null)$",
    re.IGNORECASE,
)

# --- value shapes (one list; the masker removes, the scanner detects) -----------------------------------------

_NOT_MASK = _NOT_PLACEHOLDER
KV_SECRET_KEYS = r"password|passwd|pwd|client_?secret|api_?key|account_?key|shared_?access_?key"
KV_SECRET_GENERIC_KEYS = r"secret|token"
_KV_SECRET_SEP = r"[\"']?[ \t]*:(?:[ \t]+[\"']?|[\"'])"
_KV_VALUE_END = r"[\s\"',;()\[\]{}]"
_KV_SECRET_VALUE = rf"(?![<\[{{$%])(?![A-Za-z][A-Za-z\-_.]*(?:{_KV_VALUE_END}|$))[^\s\"',;()\[\]{{}}]{{8,}}"
KV_SECRET_SRC = (
    rf"(?P<keep>(?<![^\s{{,\"'])(?:(?:{KV_SECRET_KEYS}){_KV_SECRET_SEP}"
    rf"|(?:{KV_SECRET_GENERIC_KEYS}){_KV_SECRET_SEP}(?=[^\s\"',;()\[\]{{}}]*\d))){_NOT_MASK}{_KV_SECRET_VALUE}"
)
_ASSIGN_META = (
    r"url|uri|name|path|file|header|type|mode|policy|ttl|id|expir[a-z]*|version|length|size|count|enabled|"
    r"required|prefix|suffix|format|scope|issuer|audience|provider|source|store|kind|class|method|algorithm|"
    r"strategy|cache|regex|pattern"
)

SECRET_VALUE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}(?:\.[A-Za-z0-9_\-]{8,})?")),
    ("ado_pat_52", re.compile(r"(?<![A-Za-z0-9])[a-z0-9]{52}(?![A-Za-z0-9])")),
    ("ado_pat_84", re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{84}(?![A-Za-z0-9])")),
    ("storage_key", re.compile(rf"(?i)accountkey\s*=\s*{_NOT_MASK}[A-Za-z0-9+/]{{40,}}={{0,2}}")),
    ("sas_sig", re.compile(rf"(?i)(?:[?&;]|\b)sig={_NOT_MASK}[A-Za-z0-9%+/=_\-]{{20,}}")),
    ("sas_param", re.compile(rf"(?i)sharedaccesssignature\s*=\s*{_NOT_MASK}\S{{20,}}")),
    ("sb_key", re.compile(rf"(?i)sharedaccesskey\s*=\s*{_NOT_MASK}[^;\s\"']{{20,}}")),
    ("conn_pwd", re.compile(rf"(?i)\b(?:password|pwd)\s*=\s*{_NOT_MASK}[^;\s\"']+")),
    ("conn_user", re.compile(rf"(?i)\buser\s*id\s*=\s*{_NOT_MASK}[^;\s\"']+")),
    ("kv_secret", re.compile("(?i)" + KV_SECRET_SRC)),
    ("func_code", re.compile(rf"(?i)[?&](?:code|x-functions-key)={_NOT_MASK}[A-Za-z0-9_%\-]{{20,}}")),
    ("url_userinfo", URL_USERINFO_RE),
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED |PGP |DSA )?PRIVATE KEY(?: BLOCK)?-----|PuTTY-User-Key-File-\d"
        ),
    ),
    ("appinsights", re.compile(rf"(?i)instrumentationkey\s*=\s*{_NOT_MASK}[0-9a-f\-]{{36}}")),
    (
        "guid_secret",
        re.compile(
            r"(?i)(?:instrumentation_?key|ikey|snyk[_\-]?token|api[_\-]?key|client[_\-]?secret|"
            r"subscription[_\-]?key)[\"'\s:=]{1,4}[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        ),
    ),
    (
        "vendor",
        re.compile(
            r"\b(?:(?:AKIA|ASIA)[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|"
            r"xox[baprs]-[A-Za-z0-9\-]{10,}|SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}|"
            r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{24,}|sk-ant-[A-Za-z0-9\-_]{20,}|sk-[A-Za-z0-9]{32,}|"
            r"AIza[0-9A-Za-z_\-]{35}|npm_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9\-_]{20,}|dop_v1_[a-f0-9]{64}|"
            r"pypi-[A-Za-z0-9_\-]{50,})\b"
        ),
    ),
    (
        "http_auth",
        re.compile(
            rf"(?i)(?P<keep>\bauthorization\s*[:=]\s*[\"']?(?:bearer|basic)\s+){_NOT_MASK}(?![$<\[{{%])[A-Za-z0-9+/=_\-.]{{16,}}"
        ),
    ),
    (
        "assign_secret",
        re.compile(
            r"(?i)(?<![\w.-])(?P<keep>(?:export\s+|set\s+|\$env:|\$)?"
            rf"(?![\w.-]*(?:{_ASSIGN_META})\s*=)"
            r"(?:[A-Za-z_][\w.-]*?)?(?:password|passwd|pwd|secret|token|apikey|api_key|client_secret|access_key)[\w.-]*"
            r"\s*=\s*[\"']?)"
            + _NOT_MASK
            + r"(?![<\[{$%])(?![^\s\"';]*?[A-Za-z]{4,}[_-][^\s\"';]*?[A-Za-z]{4,})"
            + r"(?=[A-Za-z0-9+/=_.!@#$%^*~-]*[\d!@#$%^*+/=~])[A-Za-z0-9+/=_.!@#$%^*~-]{12,}"
        ),
    ),
]

# --- high-entropy catch-all --------------------------------------------------------------------------------------

_ENTROPY_TOKEN_RE = re.compile(r"[A-Za-z0-9+/=_\-]{24,}")
_HEX_RE = re.compile(r"^[0-9a-fA-F\-]+$")
_GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_PATHISH_RE = re.compile(r"^[A-Za-z]:|://")


def _shannon(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    counts: dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _char_classes(s: str) -> int:
    return sum(1 for pred in (str.islower, str.isupper, str.isdigit) if any(pred(ch) for ch in s)) + (
        1 if any(not ch.isalnum() for ch in s) else 0
    )


def _is_exempt(tok: str) -> bool:
    """Identifier shapes: hex, paths, GUID-bearing ids, word-segmented and hyphenated names."""
    if len(tok) < 24 or _HEX_RE.match(tok) or _PATHISH_RE.search(tok):
        return True
    if tok.startswith("-") or PLACEHOLDER_RE.match(tok) or _GUID_RE.search(tok):
        return True
    segs = re.split(r"[/\-]", tok)
    if sum(1 for seg in segs if len(seg) >= 8 and seg.isalpha()) >= 2:
        return True
    return "-" in tok and sum(1 for seg in segs if len(seg) >= 4 and seg.isalpha()) >= 2


def _longest_case_run(tok: str) -> int:
    best = run = 0
    prev: bool | None = None
    for ch in tok:
        if ch.isalpha():
            run = run + 1 if prev is not None and ch.islower() == prev else 1
            prev = ch.islower()
        else:
            run, prev = 0, None
        best = max(best, run)
    return best


def _case_flip_rate(tok: str) -> float:
    flips = sum(1 for a, b in pairwise(tok) if a.isalpha() and b.isalpha() and a.islower() != b.islower())
    return flips / max(len(tok) - 1, 1)


def is_word_shaped(tok: str) -> bool:
    """Reads as a name a human wrote (``CustomerProductAuthorizeAttribute``) rather than a random token."""
    if not any(ch.isdigit() for ch in tok) and _longest_case_run(tok) >= 5:
        return True
    return _longest_case_run(tok) >= 7 and _case_flip_rate(tok) < 0.33


def is_high_entropy_token(tok: str) -> bool:
    if _is_exempt(tok):
        return False
    classes = _char_classes(tok)
    digits = sum(ch.isdigit() for ch in tok)
    has_sep = "/" in tok or "-" in tok
    has_both_cases = any(ch.islower() for ch in tok) and any(ch.isupper() for ch in tok)
    if len(tok) < 40:
        if classes < 3 or digits < 3 or (has_sep and digits < 5):
            return False
        return _shannon(tok) >= 4.0
    if classes < 2 or digits < 2 or (has_sep and (digits < 4 or not has_both_cases)):
        return False
    return _shannon(tok) >= 4.3


def iter_high_entropy(text: str) -> Iterator[re.Match[str]]:
    for m in _ENTROPY_TOKEN_RE.finditer(text):
        if is_high_entropy_token(m.group(0)):
            yield m


def iter_opaque(text: str) -> Iterator[re.Match[str]]:
    """Strict rule for prose: a long token that does not read as a name."""
    for m in _ENTROPY_TOKEN_RE.finditer(text):
        tok = m.group(0)
        if not _is_exempt(tok) and not is_word_shaped(tok):
            yield m


__all__ = [
    "CONN_SECRET_RE",
    "KV_SECRET_SRC",
    "MASK",
    "PLACEHOLDER_RE",
    "SECRET_VALUE_PATTERNS",
    "URL_USERINFO_RE",
    "is_high_entropy_token",
    "is_secret_name",
    "is_word_shaped",
    "iter_high_entropy",
    "iter_opaque",
    "normalize_key",
]
