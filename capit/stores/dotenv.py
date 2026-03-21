"""Dotenv-style store for capit master keys.

Stores keys in a simple text file at $HOME/.local/capit/secrets.txt
Format: PLATFORM_NAME=KEY_VALUE
"""

import os
from typing import Optional
from pathlib import Path

SECRETS_FILE = Path.home() / ".local" / "capit" / "secrets.txt"


def _ensure_secrets_file():
    """Ensure the secrets file exists."""
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SECRETS_FILE.exists():
        SECRETS_FILE.touch(mode=0o600)  # Restrictive permissions


def _load_secrets() -> dict:
    """Load all secrets from the file."""
    secrets = {}
    if SECRETS_FILE.exists():
        with open(SECRETS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    secrets[key.strip()] = value.strip()
    return secrets


def _save_secrets(secrets: dict):
    """Save all secrets to the file."""
    _ensure_secrets_file()
    with open(SECRETS_FILE, "w") as f:
        f.write("# capit master keys - DO NOT SHARE\n")
        for platform, key in sorted(secrets.items()):
            f.write(f"{platform}={key}\n")


def store_key(platform: str, key: str):
    """Store a master key for a platform."""
    secrets = _load_secrets()
    secrets[platform] = key
    _save_secrets(secrets)


def retrieve_key(platform: str) -> Optional[str]:
    """Retrieve a master key for a platform."""
    secrets = _load_secrets()
    return secrets.get(platform)


def delete_key(platform: str) -> bool:
    """Delete a master key for a platform."""
    secrets = _load_secrets()
    if platform in secrets:
        del secrets[platform]
        _save_secrets(secrets)
        return True
    return False


def list_keys() -> list:
    """List all platforms with stored keys."""
    secrets = _load_secrets()
    return list(secrets.keys())
