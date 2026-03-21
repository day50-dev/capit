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


def get_auth_path() -> Path:
    """Get the path to Opencode auth file."""
    return Path.home() / ".local" / "share" / "opencode" / "auth.json"


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation."""
    auth_path = get_auth_path()
    
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


def _display_diff(old_path: str, new_path: str):
    """Display diff between two files."""
    diff_tool = os.environ.get("DIFFTOOL", "diff --color=auto")

    try:
        if diff_tool == "diff --color=auto":
            result = subprocess.run(
                ["diff", "--color=auto", "-u", old_path, new_path],
                capture_output=False,
                text=True
            )
        elif diff_tool == "diff":
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


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Send key to Opencode by updating auth file."""
    auth_path = get_auth_path()
    
    # Ensure directory exists
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing auth
    if auth_path.exists():
        try:
            with open(auth_path, "r") as f:
                auth = json.load(f)
        except json.JSONDecodeError:
            auth = {}
    else:
        auth = {}
    
    # Create backup
    backup_path = None
    if auth_path.exists():
        backup_dir = tempfile.mkdtemp(prefix="capit-")
        backup_path = Path(backup_dir) / auth_path.name
        import shutil
        shutil.copy2(auth_path, backup_path)
    
    # Update auth with new provider
    auth[platform] = {
        "type": "api",
        "key": key
    }
    
    # Write with secure permissions
    with open(auth_path, "w") as f:
        json.dump(auth, f, indent=2)
        f.write("\n")
    auth_path.chmod(0o600)
    
    click.echo(f"${spend_cap} {platform} key installed into opencode")
    
    if backup_path:
        click.echo(f"Old configuration backed up to {backup_path}")
    
    return key
