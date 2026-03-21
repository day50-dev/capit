"""AIHubMix platform implementation for capit.

Creates API keys with spending caps using AIHubMix's Management API.
https://docs.aihubmix.com/cn/api/CliEndpoints/create-key
"""

import requests

PLATFORM_NAME = "aihubmix"
PLATFORM_URL = "https://aihubmix.com"
API_BASE = "https://aihubmix.com/api"
SETUP_URL = "https://console.aihubmix.com/setting"
SETUP_INSTRUCTIONS = "You need an access key to create capped API keys"


def validate_key(key: str) -> bool:
    """Validate an AIHubMix API key format."""
    return key.startswith("sk-")


def get_key_format() -> str:
    """Return the expected key format for documentation."""
    return "sk-..."


def list_keys(master_key: str) -> list:
    """List all API keys for this platform."""
    from datetime import datetime
    
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json",
        "User-Agent": "capit/0.2.0"
    }

    response = requests.get(f"{API_BASE}/token/", headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    keys = []
    if isinstance(data, dict) and data.get("success"):
        keys = data.get("data", [])
    elif isinstance(data, list):
        keys = data
    
    # Convert created_time (UNIX timestamp) to created_at (ISO format) for consistency
    for key in keys:
        if key.get("created_time"):
            try:
                # Convert UNIX timestamp to ISO format
                dt = datetime.fromtimestamp(key["created_time"])
                key["created_at"] = dt.isoformat()
            except (ValueError, TypeError):
                key["created_at"] = ""
        else:
            key["created_at"] = ""
        
        # Map AIHubMix quota fields to standard fields
        # used_quota / 500000 = actual usage
        if key.get("used_quota") is not None:
            key["usage"] = key["used_quota"] / 500000.0
        else:
            key["usage"] = 0
        
        # remain_quota: -1 = unlimited, otherwise quota remaining
        if key.get("unlimited_quota"):
            key["limit"] = None
        elif key.get("remain_quota"):
            # Convert remaining quota to limit (this is approximate)
            key["limit"] = key["remain_quota"] / 500000.0
        else:
            key["limit"] = None
        
        # Map status (0=disabled, 1=enabled) to disabled boolean
        key["disabled"] = key.get("status") == 0
    
    return keys


def delete_key(master_key: str, token_id: int) -> bool:
    """Delete/revoke an API key permanently."""
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json",
        "User-Agent": "capit/0.2.0"
    }

    response = requests.delete(f"{API_BASE}/token/{token_id}", headers=headers, timeout=30)
    response.raise_for_status()
    return True


def create_limited_key(master_key: str, spend_cap: str, salt: str, name: str = None, prefix: str = None) -> str:
    """Create a limited key for AIHubMix with spending cap via API.

    Calls AIHubMix's Management API to create a key with quota limit.
    Note: AIHubMix uses quota units where 1 unit = 1/500,000 of actual value.

    Args:
        master_key: Management API key
        spend_cap: Spending cap (e.g., "5.00" for $5) or "unlimited" for no cap
        salt: Unique identifier for this key
        name: Optional name for the key
        prefix: Optional prefix for organization (defaults to "capit")

    Returns:
        The created API key string (sk-...)
    """
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

    # Create key with or without quota limit
    if spend_cap == "unlimited":
        # Unlimited quota
        payload = {
            "name": key_name,
            "unlimited_quota": True,
            "expired_time": -1  # Never expires
        }
    else:
        # Convert spend cap to quota units (AIHubMix uses units where 1 = 1/500,000)
        budget_limit = float(spend_cap)
        quota_units = int(budget_limit * 500000)
        payload = {
            "name": key_name,
            "unlimited_quota": False,
            "remain_quota": quota_units,
            "expired_time": -1  # Never expires
        }
    
    response = requests.post(
        f"{API_BASE}/token/",
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    key_data = response.json()

    # Extract key from response
    if isinstance(key_data, dict) and key_data.get("success"):
        data = key_data.get("data", {})
        # AIHubMix returns the key in a specific field - check common patterns
        limited_key = (
            data.get("token") or
            data.get("key") or
            data.get("access_token") or
            data.get("api_key")
        )
        
        if not limited_key:
            # If key is not directly in response, we may need to handle differently
            # Some APIs return the key in a different format
            raise RuntimeError(f"Could not extract key from response: {key_data}")
        
        return limited_key
    
    raise RuntimeError(f"Failed to create key: {key_data}")
