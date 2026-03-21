"""Opencode agent for capit.

Automatically configures the API key in Opencode's auth file.
"""

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path

import click

from capit.agents.base import Agent, create_backup, _display_diff


class OpencodeAgent(Agent):
    """Opencode agent."""

    name = "opencode"

    def get_config_path(self) -> Path:
        """Get the path to Opencode auth file."""
        return Path.home() / ".local" / "share" / "opencode" / "auth.json"

    def show_diff(self, platform: str, spend_cap: str, agent: str = None) -> bool:
        """Show diff with opencode-specific provider structure."""
        agent = agent or self.name
        auth_path = self.get_config_path()

        # Load existing auth
        if auth_path.exists():
            try:
                with open(auth_path, "r") as f:
                    auth = json.load(f)
                old_auth = copy.deepcopy(auth)
            except json.JSONDecodeError:
                old_auth = None
        else:
            old_auth = None
            auth = {}

        # Prepare new auth with placeholder
        new_auth = copy.deepcopy(auth) if auth else {}
        new_auth[platform] = {
            "type": "api",
            "key": "<new key>"
        }

        # Create temp files for diff
        temp_fd, temp_path = tempfile.mkstemp(prefix="capit-staged-", suffix=".json")
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(new_auth, f, indent=2)
                f.write("\n")

            # Show diff if old auth exists
            if old_auth is not None:
                old_fd, old_path = tempfile.mkstemp(prefix="capit-current-", suffix=".json")
                try:
                    with os.fdopen(old_fd, "w") as f:
                        json.dump(old_auth, f, indent=2)
                        f.write("\n")

                    click.echo("Impacted changes:")
                    _display_diff(old_path, temp_path)
                finally:
                    try:
                        Path(old_path).unlink()
                    except OSError:
                        pass
            else:
                click.echo("Impacted changes:")
                click.echo("New configuration:")
                with open(temp_path, "r") as f:
                    click.echo(f.read(), err=True)

            return click.confirm(
                f"Configure {agent} with a new {platform} key (limit: ${spend_cap})?",
                default=True,
                err=True
            )
        finally:
            try:
                Path(temp_path).unlink()
            except OSError:
                pass

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
