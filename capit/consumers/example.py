"""Template for creating a new consumer for capit.

Copy this file to create a new consumer. Name it after your tool
(e.g., myagent.py for --send-to myagent).
"""

import click


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send the generated key to your tool.
    
    This function is called when a user runs:
        capit openrouter 5.00 --send-to myagent
    
    Args:
        key: The generated limited API key
        platform: The platform name (e.g., "openrouter")
        spend_cap: The spending cap (e.g., "5.00")
        
    Returns:
        The key (for potential chaining)
    """
    # Customize this for your tool
    
    # Option 1: Print instructions
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with MyAgent:", err=True)
    click.echo(f"  export API_KEY={key}", err=True)
    
    # Option 2: Write to a config file
    # from pathlib import Path
    # config_file = Path.home() / ".myagent" / "config.json"
    # config_file.parent.mkdir(parents=True, exist_ok=True)
    # import json
    # config = {"api_key": key}
    # with open(config_file, "w") as f:
    #     json.dump(config, f, indent=2)
    # click.echo(f"Config written to {config_file}", err=True)
    
    # Option 3: Call an API
    # import requests
    # requests.post("https://myagent.com/api/register-key", json={"key": key})
    
    return key
