"""OpenRouter platform implementation for capit.

Creates actual limited API keys with spending caps using OpenRouter's Management API.
https://openrouter.ai/docs/guides/overview/auth/management-api-keys
https://openrouter.ai/docs/guides/features/guardrails
"""

import requests

PLATFORM_NAME = "openrouter"
PLATFORM_URL = "https://openrouter.ai"
API_BASE = "https://openrouter.ai/api/v1"


def validate_key(key: str) -> bool:
    """Validate an OpenRouter API key format."""
    return key.startswith("sk-or-v1-")


def get_key_format() -> str:
    """Return the expected key format for documentation."""
    return "sk-or-v1-..."


def list_keys(master_key: str) -> list:
    """List all API keys for this platform."""
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json",
        "User-Agent": "capit/0.2.0"
    }
    
    response = requests.get(f"{API_BASE}/keys", headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    if isinstance(data, dict):
        return data.get("data", [])
    elif isinstance(data, list):
        return data
    return []


def delete_key(master_key: str, key_hash: str) -> bool:
    """Delete/revoke an API key permanently."""
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json",
        "User-Agent": "capit/0.2.0"
    }

    response = requests.delete(f"{API_BASE}/keys/{key_hash}", headers=headers, timeout=30)
    response.raise_for_status()
    return True


def create_limited_key(master_key: str, spend_cap: str, salt: str, name: str = None, prefix: str = None) -> str:
    """Create a limited key for OpenRouter with spending cap via API.

    Calls OpenRouter's Management API to:
    1. Create a guardrail with the spending limit
    2. Create an API key with that guardrail assigned

    Args:
        master_key: Management API key
        spend_cap: Spending cap (e.g., "1.00" for $1)
        salt: Unique identifier for this key
        name: Optional name for the key
        prefix: Optional prefix for organization (defaults to "capit")

    Returns:
        The created API key string (sk-or-v1-...)
    """
    budget_limit = float(spend_cap)

    # Default prefix to "capit" if neither prefix nor name is specified
    if not prefix and not name:
        prefix = "capit"

    # Build key name from prefix, name, and salt
    name_parts = []
    if prefix:
        name_parts.append(prefix.rstrip('-'))
    if name:
        name_parts.append(name)
    name_parts.append(salt[:8])
    key_name = "-".join(name_parts)
    
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json",
        "User-Agent": "capit/0.2.0"
    }
    
    # Step 1: Create guardrail with spending limit
    guardrail_response = requests.post(
        f"{API_BASE}/guardrails",
        headers=headers,
        json={
            "name": f"capit-guard-{salt[:8]}",
            "budget_limit": budget_limit,
            "budget_reset": "monthly"
        },
        timeout=30
    )
    guardrail_response.raise_for_status()
    guardrail_data = guardrail_response.json()
    
    # Handle response format
    if isinstance(guardrail_data, dict):
        guardrail_id = guardrail_data.get("id") or guardrail_data.get("data", {}).get("id")
    else:
        guardrail_id = None
    
    if not guardrail_id:
        raise RuntimeError(f"Failed to get guardrail ID: {guardrail_data}")
    
    # Step 2: Create API key with the guardrail
    key_response = requests.post(
        f"{API_BASE}/keys",
        headers=headers,
        json={
            "name": key_name,
            "limit": budget_limit,
            "guardrail_id": guardrail_id
        },
        timeout=30
    )
    key_response.raise_for_status()
    key_data = key_response.json()
    
    # Extract key from response
    if isinstance(key_data, dict):
        limited_key = (
            key_data.get("key") or 
            key_data.get("data", {}).get("key") or
            key_data.get("data", {}).get("token")
        )
    elif isinstance(key_data, str):
        limited_key = key_data
    else:
        limited_key = str(key_data)
    
    if not limited_key:
        raise RuntimeError(f"Failed to extract key: {key_data}")
    
    return limited_key
