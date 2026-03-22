# capit Platform Creator Skill

Add a new platform to capit with this Claude agent skill.

## Usage

Ask Claude to add a platform:

```
Add a new platform for Anthropic that creates API keys with spending limits using their API
```

## What This Skill Does

This skill helps you create a new platform for capit by:

1. Creating the platform Python file in `capit/platforms/`
2. Implementing the `create_limited_key()` function
3. Adding platform metadata (name, URL, API base)

## Example Request

```
Create a platform for Groq that creates rate-limited API keys.
Their API is at https://api.groq.com/openai/v1
```

## Output Format

The skill will create a file like:

```python
"""Groq platform implementation for capit."""

import requests

PLATFORM_NAME = "groq"
PLATFORM_URL = "https://groq.com"
API_BASE = "https://api.groq.com/openai/v1"


def validate_key(key: str) -> bool:
    """Validate a Groq API key format."""
    return key.startswith("gsk_")


def get_key_format() -> str:
    """Return the expected key format."""
    return "gsk_..."


def create_limited_key(
    master_key: str,
    spend_cap: str,
    salt: str,
    prefix: str = None
) -> str:
    """Create a rate-limited API key for Groq."""
    # Build key name from prefix and salt
    prefix = prefix or "capit"
    key_name = f"{prefix.rstrip('-')}-{salt[:8]}"
    
    # Call Groq API to create key with rate limit
    headers = {"Authorization": f"Bearer {master_key}"}
    response = requests.post(
        f"{API_BASE}/api-keys",
        headers=headers,
        json={
            "name": key_name,
            "rate_limit": int(spend_cap)  # requests per minute
        }
    )
    response.raise_for_status()
    return response.json()["key"]
```

## Platform Template

All platforms follow this pattern:

```python
"""<Platform> implementation for capit."""

import requests  # If calling external API

PLATFORM_NAME = "<platform>"
PLATFORM_URL = "https://<platform>.com"
API_BASE = "https://api.<platform>.com/v1"  # Required for online mode


def validate_key(key: str) -> bool:
    """Validate the API key format for this platform."""
    return key.startswith("sk-")


def get_key_format() -> str:
    """Return the expected key format for documentation."""
    return "sk-..."


def create_limited_key(
    master_key: str,
    spend_cap: str,
    salt: str,
    prefix: str = None
) -> str:
    """Create a limited key with spending/rate limits.

    Args:
        master_key: The master API key
        spend_cap: The spending cap (e.g., "5.00" for $5)
        salt: Random salt for uniqueness
        prefix: Optional prefix for organization

    Returns:
        The created API key string
    """
    # Build key name from prefix and salt
    prefix = prefix or "capit"
    key_name = f"{prefix.rstrip('-')}-{salt[:8]}"
    
    # Call platform API to create key with limits
    headers = {"Authorization": f"Bearer {master_key}"}
    response = requests.post(
        f"{API_BASE}/keys",
        headers=headers,
        json={"name": key_name, "limit": spend_cap}
    )
    response.raise_for_status()
    return response.json()["key"]
```

## Testing

After creating a platform, test it:

```bash
capit --platforms  # Verify it's listed
capit --keys add <platform>  # Add master key
capit <platform> 5.00  # Create limited key
```

## Platform Types

### Type 1: Online (API-based)

Calls the platform's API to create real limited keys:

```python
API_BASE = "https://api.platform.com/v1"  # Required

def create_limited_key(master_key, spend_cap, salt, prefix):
    # Call API to create actual limited key
    response = requests.post(f"{API_BASE}/keys", ...)
    return response.json()["key"]
```

### Type 2: Offline (Deterministic)

Generates deterministic keys locally (no API calls):

```python
import hashlib

def create_limited_key(master_key, spend_cap, salt, prefix):
    key_material = f"{master_key}:{spend_cap}:{salt}"
    key_hash = hashlib.sha256(key_material.encode()).hexdigest()
    return f"sk-{key_hash[:12]}-{salt}"
```

Note: Offline mode doesn't create real limits on the platform.
