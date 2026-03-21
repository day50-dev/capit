"""Example platform template for capit.

Copy this file to create a new platform implementation.
Rename the file to match your platform name (e.g., anthropic.py).
"""

import hashlib

PLATFORM_NAME = "example"
PLATFORM_URL = "https://example.com"


def validate_key(key: str) -> bool:
    """Validate the API key format for this platform."""
    return key.startswith("sk-ex-")


def get_key_format() -> str:
    """Return the expected key format for documentation."""
    return "sk-ex-..."


def create_limited_key(master_key: str, spend_cap: str, salt: str, name: str = None, prefix: str = None) -> str:
    """Create a limited key for this platform with spending cap.
    
    This is an offline implementation that generates a deterministic
    key based on the master key and spending cap. It does NOT call
    any external API.
    
    For platforms with APIs (like OpenRouter), implement actual API
    calls to create real limited keys.
    
    Args:
        master_key: The master API key
        spend_cap: The spending cap (e.g., "1.00" for $1)
        salt: A random salt for uniqueness
        name: Optional name for the key (unused in offline mode)
        prefix: Optional prefix for organization (unused in offline mode)
        
    Returns:
        A deterministic limited key string
    """
    key_material = f"{master_key}:{spend_cap}:{salt}"
    key_hash = hashlib.sha256(key_material.encode()).hexdigest()
    
    return f"sk-ex-{key_hash[:12]}-{salt}"
