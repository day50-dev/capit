"""Claude Code consumer for capit.

Automatically configures the API key in Claude Code's credentials file.
"""

import json
import click
from pathlib import Path


def get_credentials_path() -> Path:
    """Get the path to Claude Code credentials file."""
    # Check for custom config dir
    import os
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / ".credentials.json"
    
    # Default location
    return Path.home() / ".claude" / ".credentials.json"


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send key to Claude Code by updating credentials file."""
    creds_path = get_credentials_path()
    
    # Ensure directory exists
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing credentials or create new
    if creds_path.exists():
        try:
            with open(creds_path, "r") as f:
                creds = json.load(f)
        except json.JSONDecodeError:
            creds = {}
    else:
        creds = {}
    
    # Update API key
    # Claude Code uses 'api_key' for OpenRouter-compatible APIs
    creds["api_key"] = key
    
    # Write back with secure permissions
    with open(creds_path, "w") as f:
        json.dump(creds, f, indent=2)
    
    # Set secure file permissions (owner read/write only)
    creds_path.chmod(0o600)
    
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\n✅ Configured in {creds_path}", err=True)
    click.echo(f"\nStart Claude Code:", err=True)
    click.echo(f"  claude", err=True)
    
    return key
