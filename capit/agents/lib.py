"""Common utilities for capit agents.

This module provides helper functions for configuring API keys in various agents.
Most agents just need to update a JSON config file with a new API key.

This file should NOT be listed as an agent - it's a library module.
"""

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path

import click


def show_json_diff(
    config_path: Path,
    key_path: str,  # JSON path like "api_key" or "openrouter.key"
    new_value: str,
    agent: str,
    platform: str,
    spend_cap: str
) -> bool:
    """Show diff of JSON config changes and ask for confirmation.
    
    Args:
        config_path: Path to the config file
        key_path: Dot-notation path to the key field (e.g., "api_key" or "openrouter.key")
        new_value: The new value to show in the diff (typically "<new key>")
        agent: Agent name for display
        platform: Platform name for display
        spend_cap: Spending cap for display
        
    Returns:
        True if user confirmed, False if aborted
    """
    # Load existing config
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            old_config = copy.deepcopy(config)
        except json.JSONDecodeError:
            old_config = None
    else:
        old_config = None
        config = {}
    
    # Prepare new config with placeholder - handle nested paths
    new_config = copy.deepcopy(config) if config else {}
    keys = key_path.split(".")
    if len(keys) == 1:
        new_config[key_path] = new_value
    else:
        parent_key = ".".join(keys[:-1])
        field_key = keys[-1]
        if parent_key in new_config and isinstance(new_config[parent_key], dict):
            new_config[parent_key][field_key] = new_value
        else:
            new_config[parent_key] = {field_key: new_value}
    
    # Create temp files for diff
    temp_fd, temp_path = tempfile.mkstemp(prefix="capit-staged-", suffix=".json")
    try:
        with os.fdopen(temp_fd, "w") as f:
            json.dump(new_config, f, indent=2)
            f.write("\n")

        # Show diff if old config exists
        if old_config is not None:
            old_fd, old_path = tempfile.mkstemp(prefix="capit-current-", suffix=".json")
            try:
                with os.fdopen(old_fd, "w") as f:
                    json.dump(old_config, f, indent=2)
                    f.write("\n")

                click.echo("Impacted changes:")
                _display_diff(old_path, temp_path)
            finally:
                try:
                    Path(old_path).unlink()
                except:
                    pass
        else:
            # No existing config, show what will be created
            click.echo("Impacted changes:")
            click.echo("New configuration:")
            with open(temp_path, "r") as f:
                click.echo(f.read(), err=True)

        # Ask for confirmation
        return click.confirm(f"Configure {agent} with a new {platform} key (limit: ${spend_cap})?", default=True, err=True)
        
    finally:
        try:
            Path(temp_path).unlink()
        except:
            pass


def _set_nested_value(data: dict, path: str, value):
    """Set a nested value in a dict using dot notation."""
    keys = path.split(".")
    for key in keys[:-1]:
        if key not in data:
            data[key] = {}
        data = data[key]
    data[keys[-1]] = value


def _get_nested_value(data: dict, path: str, default=None):
    """Get a nested value from a dict using dot notation."""
    keys = path.split(".")
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def _display_diff(old_path: str, new_path: str):
    """Display diff between two files."""
    diff_tool = os.environ.get("DIFFTOOL", "diff")

    try:
        if diff_tool == "diff":
            result = subprocess.run(
                ["diff", "-u", old_path, new_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.echo(result.stdout, err=True)
        else:
            subprocess.run([diff_tool, old_path, new_path])
    except FileNotFoundError:
        result = subprocess.run(
            ["diff", "-u", old_path, new_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            click.echo(result.stdout, err=True)


def install_key(
    config_path: Path,
    key_path: str,
    key_value: str,
    platform: str,
    agent: str,
    spend_cap: str,
    mode: int = 0o600
) -> str:
    """Install an API key to a config file with backup.
    
    Args:
        config_path: Path to the config file
        key_path: Dot-notation path to the key field (e.g., "api_key" or "openrouter.key")
        key_value: The actual API key value
        platform: Platform name for display
        agent: Agent name for display
        spend_cap: Spending cap for display
        mode: File permissions (default 0o600)
        
    Returns:
        The key value (for chaining)
    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}
    
    # Create backup
    backup_path = None
    if config_path.exists():
        backup_dir = tempfile.mkdtemp(prefix="capit-")
        backup_path = Path(backup_dir) / config_path.name
        import shutil
        shutil.copy2(config_path, backup_path)
    
    # Update key - handle nested paths
    keys = key_path.split(".")
    if len(keys) == 1:
        # Simple path: just set the value
        config[key_path] = key_value
    else:
        # Nested path: preserve existing structure
        parent_key = ".".join(keys[:-1])
        field_key = keys[-1]
        if parent_key not in config:
            config[parent_key] = {}
        if not isinstance(config[parent_key], dict):
            # Existing value is not a dict, replace it
            config[parent_key] = {}
        config[parent_key][field_key] = key_value
    
    # Write with secure permissions
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    config_path.chmod(mode)
    
    click.echo(f"${spend_cap} {platform} key installed into {agent}")
    
    if backup_path:
        click.echo(f"Old configuration backed up to {backup_path}")
    
    return key_value


def simple_agent_send(
    key: str,
    platform: str,
    spend_cap: str,
    agent: str,
    config_path: Path,
    key_path: str = "api_key",
    mode: int = 0o600
) -> str:
    """Simple agent send function for basic JSON config updates.
    
    This is for agents that just need to set a single key field.
    For confirmation flow, use show_json_diff first.
    
    Args:
        key: The API key to install
        platform: Platform name
        spend_cap: Spending cap
        agent: Agent name
        config_path: Path to config file
        key_path: Dot-notation path to key field
        mode: File permissions
        
    Returns:
        The key value
    """
    return install_key(config_path, key_path, key, platform, agent, spend_cap, mode)
