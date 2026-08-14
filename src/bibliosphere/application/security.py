"""Password hashing — stdlib only (hashlib + secrets), no third-party dependency.

See docs/requirements.md §4.5.
"""

import hashlib
import hmac
import secrets

_ALGORITHM = "sha256"
_ITERATIONS = 200_000


def hash_password(password: str) -> tuple[str, str]:
    """Return (password_hash, salt), both hex-encoded."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return hmac.compare_digest(candidate.hex(), password_hash)
