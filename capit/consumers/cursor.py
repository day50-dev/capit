"""Cursor IDE consumer for capit."""

import click


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send key to Cursor IDE."""
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with Cursor:", err=True)
    click.echo(f"  1. Open Cursor Settings > AI > API Keys", err=True)
    click.echo(f"  2. Add this key to OpenRouter", err=True)
    return key
