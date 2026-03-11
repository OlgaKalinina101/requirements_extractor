"""Password hashing utilities.

Uses bcrypt directly to avoid passlib compatibility issues with bcrypt>=4.0
(passlib's CryptContext raises errors about __about__ attribute).
"""

import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plain password for storage."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
