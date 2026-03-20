"""Unkey platform implementation for capit.

Creates rate-limited and usage-capped API keys using Unkey's API.
https://unkey.com/docs
"""

import requests

PLATFORM_NAME = "unkey"
PLATFORM_URL = "https://unkey.com"
API_BASE = "https://api.unkey.com/v2"


def validate_key(key: str) -> bool:
    """Validate a Unkey API key format."""
    # Unkey keys can have various prefixes or none
    return len(key) > 20


def get_key_format() -> str:
    """Return the expected key format for documentation."""
    return "[prefix]_..."


def list_keys(root_key: str, api_id: str) -> list:
    """List all API keys for this API."""
    headers = {
        "Authorization": f"Bearer {root_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{API_BASE}/keys.get",
        headers=headers,
        params={"apiId": api_id},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    if isinstance(data, dict):
        return data.get("keys", [])
    return []


def delete_key(root_key: str, key_id: str) -> bool:
    """Delete/revoke an API key."""
    headers = {
        "Authorization": f"Bearer {root_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE}/keys.deleteKey",
        headers=headers,
        json={"keyId": key_id},
        timeout=30
    )
    response.raise_for_status()
    return True


def create_limited_key(
    root_key: str,
    spend_cap: str,
    salt: str,
    name: str = None,
    prefix: str = None,
    api_id: str = None,
    rate_limit: int = None
) -> str:
    """Create a limited key for Unkey with rate/usage limits.
    
    Args:
        root_key: Unkey root key (from unkey.com/settings)
        spend_cap: Spending cap (used as credit limit)
        salt: Unique identifier for this key
        name: Optional name for the key
        prefix: Optional prefix for the key
        api_id: Unkey API ID (required)
        rate_limit: Optional requests per minute limit
        
    Returns:
        The created API key string
        
    Raises:
        RuntimeError: If required parameters are missing
        requests.RequestException: If API call fails
    """
    if not api_id:
        raise RuntimeError(
            "Unkey requires an API ID.\n"
            "Set it with: capit --keys add unkey\n"
            "Then add api_id to the key metadata or use UNKEY_API_ID env var."
        )
    
    # Parse spend cap as credit limit
    credits_remaining = int(float(spend_cap) * 100)  # Convert to credits (100 credits = $1)
    
    # Build key name
    name_parts = []
    if prefix:
        name_parts.append(prefix.rstrip('-'))
    if name:
        name_parts.append(name)
    name_parts.append(salt[:8])
    key_name = "-".join(name_parts)
    
    headers = {
        "Authorization": f"Bearer {root_key}",
        "Content-Type": "application/json"
    }
    
    # Build request body
    payload = {
        "apiId": api_id,
        "name": key_name,
        "prefix": prefix.rstrip('-') if prefix else None,
        "credits": {
            "remaining": credits_remaining,
            "refill": {
                "interval": "monthly",
                "amount": credits_remaining
            }
        }
    }
    
    # Add rate limit if specified
    if rate_limit:
        payload["ratelimits"] = [
            {
                "name": "requests",
                "limit": rate_limit,
                "duration": 60000,  # 1 minute
                "autoApply": True
            }
        ]
    
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    
    response = requests.post(
        f"{API_BASE}/keys.createKey",
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    limited_key = data.get("data", {}).get("key", "")
    
    if not limited_key:
        raise RuntimeError(f"Failed to extract key from response: {data}")
    
    return limited_key
