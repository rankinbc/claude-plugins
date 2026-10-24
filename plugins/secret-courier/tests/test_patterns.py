"""Scanner and masker: every shape is found, masked, and the masked text scans clean. courier-scan: ignore-file"""

from __future__ import annotations

import pytest

from courier.scan import sanitize_text, scan_text
from tests import fixtures as fx


def _rules(text: str) -> set[str]:
    return {f.rule for f in scan_text(text)}


@pytest.mark.parametrize(
    "value, rule",
    [
        (fx.fake_jwt(), "jwt"),
        (fx.fake_pat(), "ado_pat_52"),
        (fx.fake_storage_conn(), "storage_key"),
        (fx.fake_aws_sts_id(), "vendor"),
        (fx.fake_stripe("rk_live_"), "vendor"),
        (fx.fake_stripe("sk_test_"), "vendor"),
        ("ghp_" + fx.fake_random(36), "vendor"),
        ("-----BEGIN PGP PRIVATE KEY BLOCK-----", "private_key"),
        ("PuTTY-User-Key-File-3: ssh-ed25519", "private_key"),
        (fx.fake_bearer(), "http_auth"),
        (fx.fake_bearer("Basic"), "http_auth"),
        (fx.fake_assignment("DB_PASSWORD"), "assign_secret"),
        (fx.fake_assignment("API_KEY", "$env:"), "assign_secret"),
        (fx.fake_assignment("CLIENT_SECRET", "export "), "assign_secret"),
        ("password=" + fx.fake_random(14), "conn_pwd"),
        ("https://user:" + fx.fake_random(12) + "@host.example/x", "url_userinfo"),
    ],
)
def test_shapes_are_found_and_masked(value, rule):
    text = f"before\n{value}\nafter"
    assert rule in _rules(text), (rule, _rules(text))
    masked = sanitize_text(text)
    payload = value if rule == "private_key" else value.split("=", 1)[-1].split(" ")[-1]
    assert payload not in masked
    assert scan_text(masked) == []
    assert sanitize_text(masked) == masked


@pytest.mark.parametrize(
    "text",
    [
        "token_type=bearer",
        "PasswordPolicy=strict-twelve-chars",
        "secret_name=my-kv-secret-name",
        "API_KEY_HEADER=X-Api-Key-Header",
        "password: SecretStr",
        "TOKEN_TTL_SECONDS=3600",
        "CLIENT_SECRET=${CLIENT_SECRET}",
        "DB_PASSWORD={{secret:db-password}}",
        "DB_PASSWORD=<redacted>",
        "token_url=https://login.example.com/oauth2/v2.0/token",
        "Authorization: Bearer $TOKEN",
        "git log --oneline -5 && pytest tests -q",
        "CustomerProductAuthorizeAttribute is a class name",
        "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 is a git sha",
    ],
)
def test_names_placeholders_and_identifiers_are_not_values(text):
    assert _rules(text) == set(), (text, _rules(text))
    assert sanitize_text(text) == text
