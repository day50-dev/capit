"""Windsurf IDE consumer for capit."""

import click


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send key to Windsurf IDE."""
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with Windsurf:", err=True)
    click.echo(f"  1. Open Windsurf Settings > AI", err=True)
    click.echo(f"  2. Add this key to OpenRouter", err=True)
    return key
