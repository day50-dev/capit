# capit Store Creator Skill

Add a new store to capit with this Claude agent skill.

## Usage

Ask Claude to add a store:

```
Add a new store that saves keys to AWS Secrets Manager
```

## What This Skill Does

This skill helps you create a new store for capit by:

1. Creating the store Python file in `capit/stores/`
2. Implementing the required functions (`store_key`, `retrieve_key`, `delete_key`)
3. Adding any additional helper functions

## Example Request

```
Create a store that saves master keys to environment variables with CAPIT_ prefix
```

## Output Format

The skill will create a file like:

```python
"""Environment variable store for capit master keys.

Stores keys as environment variables: CAPIT_<PLATFORM>_KEY
"""

import os


def store_key(platform: str, key: str):
    """Store a master key for a platform.
    
    Note: This store is ephemeral - keys are not persisted.
    Use dotenv store for persistent storage.
    """
    # Cannot persist to env vars from Python subprocess
    raise RuntimeError(
        "Env store cannot persist keys. "
        "Set export CAPIT_<PLATFORM>_KEY=<value> manually."
    )


def retrieve_key(platform: str) -> str | None:
    """Retrieve a master key for a platform."""
    env_var = f"CAPIT_{platform.upper()}_KEY"
    return os.environ.get(env_var)


def delete_key(platform: str) -> bool:
    """Delete a master key for a platform."""
    env_var = f"CAPIT_{platform.upper()}_KEY"
    if env_var in os.environ:
        del os.environ[env_var]
        return True
    return False
```

## Store Template

All stores follow this pattern:

```python
"""<Store Name> store for capit master keys.

<Description of storage format and location>
"""

from pathlib import Path

# Optional: define where keys are stored
STORE_PATH = Path.home() / ".config" / "capit" / "secrets"


def store_key(platform: str, key: str):
    """Store a master key for a platform.
    
    Args:
        platform: Platform name (e.g., 'openrouter')
        key: The master API key to store
    """
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "a") as f:
        f.write(f"{platform}={key}\n")


def retrieve_key(platform: str) -> str | None:
    """Retrieve a master key for a platform.
    
    Args:
        platform: Platform name
        
    Returns:
        The stored key, or None if not found
    """
    if not STORE_PATH.exists():
        return None
    with open(STORE_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line:
                key_platform, key = line.split("=", 1)
                if key_platform == platform:
                    return key
    return None


def delete_key(platform: str) -> bool:
    """Delete a master key for a platform.
    
    Args:
        platform: Platform name
        
    Returns:
        True if key was deleted, False if not found
    """
    if not STORE_PATH.exists():
        return False
    
    # Read all keys
    keys = []
    found = False
    with open(STORE_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line:
                key_platform, key = line.split("=", 1)
                if key_platform == platform:
                    found = True
                else:
                    keys.append(line)
    
    if not found:
        return False
    
    # Rewrite file without deleted key
    with open(STORE_PATH, "w") as f:
        for key in keys:
            f.write(f"{key}\n")
    
    return True
```

## Store Types

### Type 1: File-based

Stores keys in a local file (like dotenv):

```python
from pathlib import Path

SECRETS_FILE = Path.home() / ".local" / "capit" / "secrets.txt"


def store_key(platform: str, key: str):
    secrets = _load_secrets()
    secrets[platform] = key
    _save_secrets(secrets)


def retrieve_key(platform: str) -> str | None:
    secrets = _load_secrets()
    return secrets.get(platform)
```

### Type 2: External Secret Manager

Stores keys in an external service (AWS, GCP, etc.):

```python
import boto3

def store_key(platform: str, key: str):
    client = boto3.client("secretsmanager")
    client.put_secret_value(
        SecretId=f"capit/{platform}",
        SecretString=key
    )


def retrieve_key(platform: str) -> str | None:
    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=f"capit/{platform}")
        return response["SecretString"]
    except client.exceptions.ResourceNotFoundException:
        return None
```

### Type 3: Ephemeral

Keys are not persisted (for testing):

```python
_ephemeral_keys = {}


def store_key(platform: str, key: str):
    _ephemeral_keys[platform] = key


def retrieve_key(platform: str) -> str | None:
    return _ephemeral_keys.get(platform)
```

## Testing

After creating a store, test it:

```bash
capit --stores  # Verify it's listed
capit --keys add openrouter  # Add a test key
capit openrouter 5.00  # Create limited key
```

## Store Functions

### Required

| Function | Purpose |
|----------|---------|
| `store_key(platform, key)` | Store a master key |
| `retrieve_key(platform)` | Get a stored key |
| `delete_key(platform)` | Remove a stored key |

### Optional

| Function | Purpose |
|----------|---------|
| `list_keys()` | List all stored platforms |

## Security Best Practices

1. **File permissions**: Restrict access to secret files
   ```python
   SECRETS_FILE.touch(mode=0o600)  # Owner read/write only
   ```

2. **Encryption**: Consider encrypting keys at rest

3. **Audit logging**: Log access for compliance

4. **Rotation**: Support key rotation if applicable

## Example: 1Password Store

```python
"""1Password store for capit master keys.

Uses 1Password CLI (op) to store and retrieve keys.
Requires: https://developer.1password.com/docs/cli/
"""

import subprocess


def _run_op(args: list) -> str:
    """Run 1Password CLI command."""
    result = subprocess.run(
        ["op"] + args,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def store_key(platform: str, key: str):
    """Store a master key in 1Password."""
    vault = "capit"  # Or get from config
    try:
        # Create item
        _run_op([
            "item", "create",
            f"--vault={vault}",
            f"--title={platform} master key",
            f"password={key}"
        ])
    except subprocess.CalledProcessError:
        # Item exists, update it
        _run_op([
            "item", "edit",
            f"--vault={vault}",
            f"{platform}",
            f"password={key}"
        ])


def retrieve_key(platform: str) -> str | None:
    """Retrieve a master key from 1Password."""
    try:
        return _run_op([
            "item", "get",
            platform,
            "--fields", "label=password"
        ])
    except subprocess.CalledProcessError:
        return None


def delete_key(platform: str) -> bool:
    """Delete a master key from 1Password."""
    try:
        _run_op(["item", "delete", platform])
        return True
    except subprocess.CalledProcessError:
        return False
```
