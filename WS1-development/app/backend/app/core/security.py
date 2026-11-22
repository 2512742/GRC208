"""Passwords, session tokens and CSRF tokens.

- Passwords: Argon2 (pwdlib's recommended hasher). Hashes are upgraded on login if the
  parameters change.
- Sessions: a random 256-bit token in an HttpOnly cookie; only its SHA-256 is stored, so a
  database leak doesn't hand out live sessions.
- CSRF: double-submit, bound to the session. The token is an HMAC of the session token, so it
  can't be forged or planted from another site; the client echoes it in the X-CSRF-Token header
  on every state-changing request.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()

# Verified when the username doesn't exist, so a login takes the same time either way and
# can't reveal which usernames are real.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Return (matches, upgraded_hash_or_None). Never raises on malformed hashes."""
    if not password_hash:
        _hasher.verify(password, _DUMMY_HASH)
        return False, None
    try:
        return _hasher.verify_and_update(password, password_hash)
    except Exception:  # malformed or foreign hash: treat as a failed login
        return False, None


def burn_password_check(password: str) -> None:
    """Spend the same effort as a real check (unknown username)."""
    _hasher.verify(password, _DUMMY_HASH)


def password_problems(password: str, username: str | None = None) -> list[str]:
    problems = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append(f"at most {PASSWORD_MAX_LENGTH} characters")
    if password.strip() != password:
        problems.append("no leading or trailing spaces")
    if username and username.lower() in password.lower():
        problems.append("must not contain the username")
    if len(set(password)) < 5:
        problems.append("at least 5 different characters")
    return problems


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token_for(session_token: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"), f"csrf:{session_token}".encode(), hashlib.sha256
    ).hexdigest()


def csrf_matches(given: str | None, expected: str) -> bool:
    return bool(given) and hmac.compare_digest(given or "", expected)
