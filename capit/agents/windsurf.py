"""Windsurf IDE agent for capit.

Automatically configures the API key in Windsurf's settings.
"""

from pathlib import Path

from capit.agents.lib import show_json_diff, install_key


def get_settings_path() -> Path:
    """Get the path to Windsurf settings file."""
    return Path.home() / ".config" / "Windsurf" / "User" / "settings.json"


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation."""
    return show_json_diff(
        get_settings_path(),
        "openrouter.apiKey",
        "<new key>",
        agent,
        platform,
        spend_cap
    )


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Send key to Windsurf by updating settings file."""
    return install_key(
        get_settings_path(),
        "openrouter.apiKey",
        key,
        platform,
        "windsurf",
        spend_cap
    )
