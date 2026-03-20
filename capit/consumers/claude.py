"""Claude / Claude Code consumer for capit."""

import click


def send(key: str, platform: str, spend_cap: str) -> str:
    """Send key to Claude by setting environment variable and providing instructions."""
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with Claude, run:", err=True)
    click.echo(f"  export OPENROUTER_API_KEY={key}", err=True)
    click.echo(f"\nOr pipe to claude-code:", err=True)
    click.echo(f"  OPENROUTER_API_KEY={key} claude", err=True)
    return key
