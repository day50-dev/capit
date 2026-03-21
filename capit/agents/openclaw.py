"""OpenClaw agent for capit.

Automatically configures API keys in OpenClaw's configuration.
OpenClaw uses a gateway-based system with secrets management.
https://docs.openclaw.ai/
"""

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path

import click


def get_config_dir() -> Path:
    """Get the OpenClaw configuration directory."""
    return Path.home() / ".openclaw"


def get_secrets_path() -> Path:
    """Get the path to OpenClaw secrets file."""
    return get_config_dir() / "secrets.json"


def get_config_path() -> Path:
    """Get the path to OpenClaw main config file."""
    return get_config_dir() / "openclaw.json"


def _get_provider_config(platform: str):
    """Get provider name and env var for a platform."""
    platform_mapping = {
        "openrouter": ("openrouter", "OPENROUTER_API_KEY"),
        "openai": ("openai", "OPENAI_API_KEY"),
        "anthropic": ("anthropic", "ANTHROPIC_API_KEY"),
        "groq": ("groq", "GROQ_API_KEY"),
        "google": ("google", "GOOGLE_API_KEY"),
        "gemini": ("google", "GOOGLE_API_KEY"),
    }
    return platform_mapping.get(
        platform.lower(),
        (platform.lower(), f"{platform.upper()}_API_KEY")
    )


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation."""
    config_dir = get_config_dir()
    secrets_path = get_secrets_path()
    config_path = get_config_path()
    
    config_dir.mkdir(parents=True, exist_ok=True)
    provider_name, env_var = _get_provider_config(platform)
    
    # Load existing secrets
    if secrets_path.exists():
        try:
            with open(secrets_path, "r") as f:
                secrets = json.load(f)
            old_secrets = copy.deepcopy(secrets)
        except json.JSONDecodeError:
            old_secrets = None
    else:
        old_secrets = None
        secrets = {}
    
    # Prepare new secrets with placeholder
    new_secrets = copy.deepcopy(secrets) if secrets else {}
    if "providers" not in new_secrets:
        new_secrets["providers"] = {}
    new_secrets["providers"][provider_name] = {
        "source": "env",
        "value": "<new key>"
    }
    
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
    
    # Prepare new config with placeholder
    new_config = copy.deepcopy(config) if config else {}
    if "models" not in new_config:
        new_config["models"] = {}
    if "providers" not in new_config["models"]:
        new_config["models"]["providers"] = {}
    new_config["models"]["providers"][provider_name] = {
        "apiKey": {
            "source": "env",
            "provider": provider_name,
            "id": env_var
        }
    }
    
    # Create temp files and show diff
    secrets_temp_fd, secrets_temp_path = tempfile.mkstemp(prefix="capit-secrets-", suffix=".json")
    config_temp_fd, config_temp_path = tempfile.mkstemp(prefix="capit-config-", suffix=".json")
    
    try:
        with os.fdopen(secrets_temp_fd, "w") as f:
            json.dump(new_secrets, f, indent=2)
            f.write("\n")
        
        with os.fdopen(config_temp_fd, "w") as f:
            json.dump(new_config, f, indent=2)
            f.write("\n")
        
        click.echo(f"\nConfigure {agent} with a new {platform} key (limit: ${spend_cap})?")
        click.echo("Changes:")
        
        diff_tool = os.environ.get("DIFFTOOL", "diff")
        
        # Show secrets diff
        if old_secrets is not None:
            _show_file_diff(old_secrets, secrets_temp_path, "secrets.json", diff_tool)
        
        # Show config diff
        if old_config is not None:
            _show_file_diff(old_config, config_temp_path, "openclaw.json", diff_tool)
        
        return click.confirm("Continue?", default=True, err=True)
        
    finally:
        for p in [secrets_temp_path, config_temp_path]:
            try:
                Path(p).unlink()
            except:
                pass


def _show_file_diff(old_data, new_path, label, diff_tool):
    """Show diff for a single file."""
    old_fd, old_path = tempfile.mkstemp(prefix=f"capit-old-{label}-", suffix=".json")
    try:
        with os.fdopen(old_fd, "w") as f:
            json.dump(old_data, f, indent=2)
            f.write("\n")
        
        try:
            if diff_tool == "diff":
                result = subprocess.run(
                    ["diff", "-u", old_path, new_path],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    click.echo(f"{label}:\n{result.stdout}", err=True)
            else:
                click.echo(f"{label}:", err=True)
                subprocess.run([diff_tool, old_path, new_path])
        except FileNotFoundError:
            result = subprocess.run(
                ["diff", "-u", old_path, new_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.echo(f"{label}:\n{result.stdout}", err=True)
    finally:
        try:
            Path(old_path).unlink()
        except:
            pass


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Configure API key in OpenClaw."""
    config_dir = get_config_dir()
    secrets_path = get_secrets_path()
    config_path = get_config_path()
    
    config_dir.mkdir(parents=True, exist_ok=True)
    provider_name, env_var = _get_provider_config(platform)
    
    # Load or create secrets
    if secrets_path.exists():
        try:
            with open(secrets_path, "r") as f:
                secrets = json.load(f)
        except json.JSONDecodeError:
            secrets = {}
    else:
        secrets = {}
    
    # Load or create config
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}
    
    # Create backups
    backup_dir = tempfile.mkdtemp(prefix="capit-")
    backup_paths = []
    
    for src_path, name in [(secrets_path, "secrets.json"), (config_path, "openclaw.json")]:
        if src_path.exists():
            backup_file = Path(backup_dir) / name
            import shutil
            shutil.copy2(src_path, backup_file)
            backup_paths.append(backup_file)
    
    # Update secrets
    if "providers" not in secrets:
        secrets["providers"] = {}
    secrets["providers"][provider_name] = {
        "source": "env",
        "value": key
    }
    
    # Update config
    if "models" not in config:
        config["models"] = {}
    if "providers" not in config["models"]:
        config["models"]["providers"] = {}
    config["models"]["providers"][provider_name] = {
        "apiKey": {
            "source": "env",
            "provider": provider_name,
            "id": env_var
        }
    }
    
    # Write secrets
    with open(secrets_path, "w") as f:
        json.dump(secrets, f, indent=2)
        f.write("\n")
    secrets_path.chmod(0o600)
    
    # Write config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    
    click.echo(f"${spend_cap} {platform} key installed into openclaw")
    
    if backup_paths:
        click.echo(f"Old configuration backed up to {backup_dir}")
    
    return key
