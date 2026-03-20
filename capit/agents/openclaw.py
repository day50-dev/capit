"""OpenClaw consumer for capit.

Automatically configures API keys in OpenClaw's configuration.
OpenClaw uses a gateway-based system with secrets management.
https://docs.openclaw.ai/
"""

import json
import click
from pathlib import Path


def get_config_dir() -> Path:
    """Get the OpenClaw configuration directory."""
    return Path.home() / ".openclaw"


def get_secrets_path() -> Path:
    """Get the path to OpenClaw secrets file."""
    return get_config_dir() / "secrets.json"


def get_config_path() -> Path:
    """Get the path to OpenClaw main config file."""
    return get_config_dir() / "openclaw.json"


def send(key: str, platform: str, spend_cap: str) -> str:
    """Configure API key in OpenClaw."""
    config_dir = get_config_dir()
    secrets_path = get_secrets_path()
    config_path = get_config_path()
    
    # Ensure directory exists
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Map platform to OpenClaw provider name and env var
    platform_mapping = {
        "openrouter": ("openrouter", "OPENROUTER_API_KEY"),
        "openai": ("openai", "OPENAI_API_KEY"),
        "anthropic": ("anthropic", "ANTHROPIC_API_KEY"),
        "groq": ("groq", "GROQ_API_KEY"),
        "google": ("google", "GOOGLE_API_KEY"),
        "gemini": ("google", "GOOGLE_API_KEY"),
    }
    
    provider_name, env_var = platform_mapping.get(
        platform.lower(), 
        (platform.lower(), f"{platform.upper()}_API_KEY")
    )
    
    # Load or create secrets file
    if secrets_path.exists():
        try:
            with open(secrets_path, "r") as f:
                secrets = json.load(f)
        except json.JSONDecodeError:
            secrets = {}
    else:
        secrets = {}
    
    # Ensure providers section exists
    if "providers" not in secrets:
        secrets["providers"] = {}
    
    # Add/update the API key as an environment variable source
    secrets["providers"][provider_name] = {
        "source": "env",
        "value": key
    }
    
    # Write secrets file with secure permissions
    with open(secrets_path, "w") as f:
        json.dump(secrets, f, indent=2)
    secrets_path.chmod(0o600)
    
    # Update main config to reference the secret
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}
    
    # Ensure models.providers section exists
    if "models" not in config:
        config["models"] = {}
    if "providers" not in config["models"]:
        config["models"]["providers"] = {}
    
    # Configure the provider to use the secret
    config["models"]["providers"][provider_name] = {
        "apiKey": {
            "source": "env",
            "provider": provider_name,
            "id": env_var
        }
    }
    
    # Write config file
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # Clean output matching README style
    click.echo(f"${spend_cap} {platform} key installed into openclaw")
    
    return key
