"""Opencode agent for capit.

Automatically configures the API key in Opencode's auth file.
"""

from pathlib import Path

from capit.agents.base import Agent, show_json_diff, create_backup
import click


class OpencodeAgent(Agent):
    """Opencode agent."""

    name = "opencode"

    def get_config_path(self) -> Path:
        """Get the path to Opencode auth file."""
        return Path.home() / ".local" / "share" / "opencode" / "auth.json"

    def get_key_path(self, platform: str = None) -> str:
        """Opencode uses platform-specific nested paths."""
        return f"{platform}.key"

    def _prepare_config(self, config: dict, key: str, platform: str) -> dict:
        """Prepare opencode config with provider structure."""
        config[platform] = {
            "type": "api",
            "key": key
        }
        return config


# Module-level functions for backwards compatibility
_agent = OpencodeAgent()
show_diff = _agent.show_diff
send = _agent.send
get_auth_path = _agent.get_config_path
