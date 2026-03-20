# capit Consumer Skill

Add a new consumer to capit with this Claude agent skill.

## Usage

Ask Claude to add a consumer:

```
Add a new consumer for my-agent that writes the API key to ~/.myagent/config.json
```

## What This Skill Does

This skill helps you create a new consumer for capit by:

1. Creating the consumer Python file in `capit/consumers/`
2. Implementing the `send()` function with your specified config path
3. Updating the consumer list

## Example Request

```
Create a consumer for windsurf that writes to ~/.config/Windsurf/User/settings.json
with the key stored as openrouter.apiKey
```

## Output Format

The skill will create a file like:

```python
"""Windsurf consumer for capit."""

import json
from pathlib import Path
import click


def send(key: str, platform: str, spend_cap: str) -> str:
    """Configure API key in Windsurf."""
    settings_path = Path.home() / ".config" / "Windsurf" / "User" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}
    
    settings["openrouter.apiKey"] = key
    
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    
    click.echo(f"${spend_cap} {platform} key installed into windsurf")
    return key
```

## Consumer Template

All consumers follow this pattern:

```python
"""<Agent Name> consumer for capit."""

import json  # or other config format
from pathlib import Path
import click


def get_config_path() -> Path:
    """Get the config file path for this agent."""
    return Path.home() / ".config" / "<Agent>" / "settings.json"


def send(key: str, platform: str, spend_cap: str) -> str:
    """Configure API key for this agent."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config or create new
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {}
    
    # Set the API key (customize the key name)
    config["api_key"] = key  # or config["openrouter.apiKey"] = key
    
    # Write back
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # Output in capit's standard format
    click.echo(f"${spend_cap} {platform} key installed into <agent>")
    return key
```

## Testing

After creating a consumer, test it:

```bash
capit --consumers  # Verify it's listed
capit openrouter 5.00 --agent <your-agent> -y  # Test it
```
