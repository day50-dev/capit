"""Template for creating a new agent for capit.

Copy this file to create a new agent. Name it after your tool
(e.g., myagent.py for --agent myagent).
"""

from pathlib import Path

from capit.agents.lib import show_json_diff, install_key


def get_config_path() -> Path:
    """Get the config file path for this agent."""
    return Path.home() / ".myagent" / "config.json"


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation."""
    return show_json_diff(
        get_config_path(),
        "api_key",
        "<new key>",
        agent,
        platform,
        spend_cap
    )


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Send the generated key to your tool.
    
    This function is called when a user runs:
        capit openrouter 5.00 --agent myagent
    """
    return install_key(
        get_config_path(),
        "api_key",
        key,
        platform,
        "myagent",
        spend_cap
    )
