"""Cursor IDE consumer for capit.

Automatically configures the API key in Cursor's settings.
"""

import json
import click
from pathlib import Path


def get_settings_path() -> Path:
    """Get the path to Cursor settings file."""
    # Cursor stores settings in VS Code compatible location
    return Path.home() / ".config" / "Cursor" / "User" / "settings.json"


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send key to Cursor by updating settings file."""
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
    
    click.echo(f"${spend_cap} {platform} key installed into cursor")
    
    return key
