"""Windsurf IDE consumer for capit.

Automatically configures the API key in Windsurf's settings.
"""

import json
import click
from pathlib import Path


def get_settings_path() -> Path:
    """Get the path to Windsurf settings file."""
    return Path.home() / ".config" / "Windsurf" / "User" / "settings.json"


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send key to Windsurf by updating settings file."""
    settings_path = get_settings_path()
    
    # Ensure directory exists
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing settings or create new
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}
    
    # Update API key for OpenRouter
    settings["openrouter.apiKey"] = key
    
    # Write back
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\n✅ Configured in {settings_path}", err=True)
    click.echo(f"\nRestart Windsurf for changes to take effect.", err=True)
    
    return key
