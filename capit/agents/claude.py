"""Claude Code agent for capit.

Automatically configures the API key in Claude Code's credentials file.
"""

from pathlib import Path
import os

from capit.agents.lib import show_json_diff, install_key


def get_credentials_path() -> Path:
    """Get the path to Claude Code credentials file."""
    # Check for custom config dir
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / ".credentials.json"
    
    # Default location
    return Path.home() / ".claude" / ".credentials.json"


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation."""
    return show_json_diff(
        get_credentials_path(),
        "api_key",
        "<new key>",
        agent,
        platform,
        spend_cap
    )


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Send key to Claude Code by updating credentials file."""
    return install_key(
        get_credentials_path(),
        "api_key",
        key,
        platform,
        "claude",
        spend_cap
    )
