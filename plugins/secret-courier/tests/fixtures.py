"""Secret-shaped strings built at runtime so the repo never holds one. courier-scan: ignore-file"""

from __future__ import annotations

import base64
import random
import string

_rng = random.Random(20261020)


def _alnum(n: int, alphabet: str = string.ascii_letters + string.digits) -> str:
    return "".join(_rng.choice(alphabet) for _ in range(n))


def fake_jwt() -> str:
    seg = lambda o: base64.urlsafe_b64encode(o.encode()).decode().rstrip("=")  # noqa: E731
    return (
        "eyJ"
        + seg('{"alg":"HS256","typ":"JWT"}')[3:]
        + "."
        + seg('{"sub":"pester","iat":1700000000}')
        + "."
        + _alnum(43)
    )


def fake_pat() -> str:
    return _alnum(52, string.ascii_lowercase + string.digits)


def fake_storage_key() -> str:
    return base64.b64encode(bytes(_rng.getrandbits(8) for _ in range(64))).decode()


def fake_storage_conn() -> str:
    return (
        "DefaultEndpointsProtocol=https;AccountName=fakeacct;"
        f"AccountKey={fake_storage_key()};EndpointSuffix=core.windows.net"
    )


def fake_aws_sts_id() -> str:
    return "ASIA" + _alnum(16, string.ascii_uppercase + string.digits)


def fake_stripe(prefix: str = "rk_live_") -> str:
    return prefix + _alnum(28)


def fake_bearer(scheme: str = "Bearer") -> str:
    return f"Authorization: {scheme} " + _alnum(40)


def fake_assignment(key: str, prefix: str = "") -> str:
    return f"{prefix}{key}=" + _alnum(7) + "7" + _alnum(8)


def fake_random(n: int = 32) -> str:
    return _alnum(n)
