# Adding a New Platform to capit

This guide shows you how to add support for a new API platform to capit.

## Overview

Platforms are modular Python files located in the `capit/platforms/` directory. Each platform file defines how to interact with that platform's API for creating limited keys.

## Creating a New Platform

1. Copy the example template:
   ```bash
   cp capit/platforms/example.py capit/platforms/yourplatform.py
   ```

2. Edit the file and implement the required functions:

```python
"""YourPlatform platform implementation for capit."""

import hashlib
import requests  # If calling external API

PLATFORM_NAME = "yourplatform"
PLATFORM_URL = "https://yourplatform.com"
API_BASE = "https://api.yourplatform.com/v1"  # Required for online mode


def validate_key(key: str) -> bool:
    """Validate the API key format for this platform."""
    return key.startswith("sk-yp-")


def get_key_format() -> str:
    """Return the expected key format for documentation."""
    return "sk-yp-..."


def create_limited_key(master_key: str, spend_cap: str, salt: str, name: str = None, prefix: str = None) -> str:
    """Create a limited key with spending cap.
    
    Args:
        master_key: The master API key
        spend_cap: The spending cap (e.g., "1.00" for $1)
        salt: A random salt for uniqueness
        name: Optional name for the key (e.g., "production", "testing")
        prefix: Optional prefix for organization (e.g., "prod-", "dev-")
        
    Returns:
        A limited key string
    """
    # Build key name from prefix, name, and salt
    name_parts = []
    if prefix:
        name_parts.append(prefix.rstrip('-'))
    if name:
        name_parts.append(name)
    name_parts.append(salt[:8])
    key_name = "-".join(name_parts)
    
    # Option 1: Call platform API
    # response = requests.post(...)
    # return response.json()['key']
    
    # Option 2: Generate offline (deterministic)
    key_material = f"{master_key}:{spend_cap}:{salt}"
    key_hash = hashlib.sha256(key_material.encode()).hexdigest()
    return f"sk-yp-{key_hash[:12]}-{salt}"
```

## Example: OpenRouter Integration

The OpenRouter platform shows a real integration that calls the platform API:

```python
"""OpenRouter platform implementation for capit."""

import requests

PLATFORM_NAME = "openrouter"
PLATFORM_URL = "https://openrouter.ai"
API_BASE = "https://openrouter.ai/api/v1"


def validate_key(key: str) -> bool:
    return key.startswith("sk-or-v1-")


def get_key_format() -> str:
    return "sk-or-v1-..."


def create_limited_key(master_key: str, spend_cap: str, salt: str) -> str:
    """Create a limited key for OpenRouter with spending cap via API.
    
    Calls OpenRouter's Management API to:
    1. Create a guardrail with the spending limit
    2. Create an API key with that guardrail assigned
    """
    budget_limit = float(spend_cap)
    key_name = f"capit-{salt[:8]}"
    
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json"
    }
    
    # Create guardrail with budget limit
    guardrail_response = requests.post(
        f"{API_BASE}/guardrails",
        headers=headers,
        json={
            "name": f"capit-guard-{salt[:8]}",
            "budget_limit": budget_limit,
            "budget_reset": "monthly"
        }
    )
    guardrail_response.raise_for_status()
    guardrail_id = guardrail_response.json()["id"]
    
    # Create API key with the guardrail
    key_response = requests.post(
        f"{API_BASE}/keys/",
        headers=headers,
        json={
            "name": key_name,
            "limit": budget_limit,
            "guardrail_id": guardrail_id
        }
    )
    key_response.raise_for_status()
    
    return key_response.json()["key"]
```

## Testing Your Platform

1. Add a master key for your platform:
   ```bash
   $ capit --keys add yourplatform
   ```

2. Issue a limited key:
   ```bash
   $ capit yourplatform 5.00
   ```

## Platform Conventions

- Platform files should be auditable and locally run
- Keep dependencies minimal (add to `pyproject.toml` if needed)
- Document any API endpoints used
- Include validation for key formats
- Consider rate limiting if calling external APIs
- Handle errors gracefully with informative messages

## Disabling a Platform

To temporarily disable a platform without deleting it:

```bash
$ capit --disable yourplatform
```

To re-enable:

```bash
$ capit --enable yourplatform
```

## Sharing Platforms

Share your platform implementations with the community by submitting them to the main repository or hosting them in your own repository.
