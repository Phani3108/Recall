"""Credential encryption — Fernet-based symmetric encryption for integration tokens.

Wraps credentials before storing in the database and decrypts on retrieval.
Uses the app_secret_key (hashed to 32 bytes) as the Fernet key.
"""

import base64
import hashlib
import logging
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from the app secret."""
    raw = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def _get_fernet() -> Fernet:
    return Fernet(_derive_key(settings.app_secret_key))


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    """Encrypt a credentials dict into a Fernet-encrypted string.

    Returns a base64-encoded encrypted string safe for database storage.
    """
    plaintext = json.dumps(credentials, separators=(",", ":")).encode("utf-8")
    return _get_fernet().encrypt(plaintext).decode("utf-8")


def decrypt_credentials(encrypted: str) -> dict[str, Any]:
    """Decrypt a Fernet-encrypted credentials string back to a dict.

    Returns the original credentials dict.
    Raises ValueError if decryption fails (wrong key, tampered data).
    """
    try:
        plaintext = _get_fernet().decrypt(encrypted.encode("utf-8"))
        return json.loads(plaintext)
    except InvalidToken:
        raise ValueError("Failed to decrypt credentials — key mismatch or tampered data")
    except json.JSONDecodeError:
        raise ValueError("Decrypted data is not valid JSON")


def is_encrypted(value: str) -> bool:
    """Check if a string looks like Fernet-encrypted data."""
    try:
        raw = base64.urlsafe_b64decode(value.encode("utf-8"))
        return len(raw) >= 57  # Fernet minimum: version(1) + timestamp(8) + iv(16) + block(16+16)
    except Exception:
        return False


def mask_credentials(credentials: dict[str, Any]) -> dict[str, str]:
    """Return a masked version of credentials for display (e.g., "sk-••••••3aB7")."""
    masked: dict[str, str] = {}
    for key, value in credentials.items():
        if not value or not isinstance(value, str):
            masked[key] = str(value) if value else ""
            continue
        v = str(value)
        if len(v) <= 8:
            masked[key] = "••••••"
        else:
            masked[key] = f"{v[:3]}••••••{v[-4:]}"
    return masked
