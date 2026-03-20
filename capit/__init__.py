#!/usr/bin/env python3
"""capit - Issue authentication keys with spending caps.

Usage:
    capit openrouter 1.00                    # Issue a limited key
    capit openrouter 1.00 --name prod        # With a name
    capit openrouter 1.00 --send-to claude   # Send to consumer
    capit --keys list                        # List master keys
    capit --keys remote openrouter           # List API keys from platform
    capit --platforms                        # List platforms
"""

import sys
import os
import json
import hashlib
import secrets
import logging
import shutil
from pathlib import Path
from datetime import datetime

import click

# Configuration directory
CAPIT_DIR = Path.home() / ".local" / "capit"
SCRIPT_DIR = Path(__file__).parent
PLATFORMS_DIR = SCRIPT_DIR / "platforms"
STORES_DIR = SCRIPT_DIR / "stores"
MASTER_LOOKUP_FILE = CAPIT_DIR / "master-lookup"

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('capit')


def ensure_capit_dir():
    """Ensure the capit configuration directory exists."""
    CAPIT_DIR.mkdir(parents=True, exist_ok=True)


def load_master_lookup():
    """Load the master key lookup table."""
    if not MASTER_LOOKUP_FILE.exists():
        return {}
    with open(MASTER_LOOKUP_FILE, "r") as f:
        return json.load(f)


def save_master_lookup(lookup):
    """Save the master key lookup table."""
    ensure_capit_dir()
    with open(MASTER_LOOKUP_FILE, "w") as f:
        json.dump(lookup, f, indent=2)


def get_platform_module(platform_name):
    """Dynamically load a platform module."""
    platform_file = PLATFORMS_DIR / f"{platform_name}.py"
    if not platform_file.exists():
        raise click.ClickException(f"Platform '{platform_name}' not found")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(platform_name, platform_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_store_module(store_name):
    """Dynamically load a store module."""
    store_file = STORES_DIR / f"{store_name}.py"
    if not store_file.exists():
        raise click.ClickException(f"Store '{store_name}' not found")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(store_name, store_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_platforms():
    """List all available platforms."""
    platforms = []
    if PLATFORMS_DIR.exists():
        for f in PLATFORMS_DIR.glob("*.py"):
            if f.name != "__init__.py" and not f.name.endswith(".disabled"):
                platforms.append(f.stem)
    return platforms


def list_stores():
    """List all available stores."""
    stores = []
    if STORES_DIR.exists():
        for f in STORES_DIR.glob("*.py"):
            if f.name != "__init__.py":
                stores.append(f.stem)
    return stores


def get_master_key(platform, store_name=None, interactive=False):
    """Get master key for a platform, optionally prompting interactively."""
    lookup = load_master_lookup()
    
    if platform in lookup:
        store_name = store_name or lookup[platform].get("store", "dotenv")
        store_module = get_store_module(store_name)
        master_key = store_module.retrieve_key(platform)
        if master_key:
            return master_key, store_name
    
    # Key not found - prompt interactively if allowed
    if interactive:
        click.echo(f"\nNo master key found for '{platform}'.", err=True)
        click.echo("Enter your management API key (won't be stored):", err=True)
        master_key = click.prompt("Key", hide_input=True)
        return master_key, "ephemeral"
    
    return None, None


def do_issue(platform, spend_cap, name=None, prefix=None, verbose=False, interactive=False, send_to=None, confirm=True):
    """Issue a limited key for a platform with a spending cap."""
    ensure_capit_dir()

    if verbose:
        logger.setLevel(logging.DEBUG)
        click.echo(f"Looking up platform: {platform}", err=True)

    # Get master key (may prompt interactively)
    master_key, store_name = get_master_key(platform, interactive=interactive)

    if not master_key:
        store_info = f" from store '{store_name}'" if store_name else ""
        raise click.ClickException(
            f"No master key found for platform '{platform}'{store_info}.\n"
            f"Add one with: capit --keys add {platform}\n"
            f"Or run with --interactive to enter it once."
        )
    
    if verbose:
        if store_name == "ephemeral":
            click.echo("Using ephemeral key (not stored)", err=True)
        else:
            click.echo(f"Using store: {store_name}", err=True)
            click.echo(f"Master key found (format: {master_key[:12]}...)", err=True)

    # Load platform module
    platform_module = get_platform_module(platform)

    if verbose:
        click.echo(f"Loaded platform module: {platform_module.PLATFORM_NAME}", err=True)

    # Check if platform supports online key creation (has API_BASE constant)
    if hasattr(platform_module, 'create_limited_key') and hasattr(platform_module, 'API_BASE'):
        if verbose:
            click.echo("Platform uses online key creation (API calls)", err=True)

        salt = secrets.token_hex(8)
        try:
            limited_key = platform_module.create_limited_key(master_key, spend_cap, salt, name=name, prefix=prefix)
            if verbose:
                click.echo(f"Key created successfully via API", err=True)
            
            # Handle send-to integration
            if send_to:
                return handle_send_to(send_to, limited_key, platform, spend_cap, confirm=confirm)

            return limited_key
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                raise click.ClickException(
                    f"API authentication failed. Your management key may be invalid.\n"
                    f"Get a new key from: {platform_module.PLATFORM_URL}/settings/management-keys"
                )
            elif "403" in error_msg or "Forbidden" in error_msg:
                raise click.ClickException(
                    f"API access forbidden. Your management key lacks required permissions."
                )
            elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                raise click.ClickException(
                    f"Network error: Could not connect to {platform_module.PLATFORM_URL}"
                )
            else:
                raise click.ClickException(
                    f"Failed to create limited key via API:\n{error_msg}"
                )

    # Platform doesn't support online creation - use offline mode
    if verbose:
        click.echo("Platform uses offline key generation (no API calls)", err=True)

    salt = secrets.token_hex(8)
    key_material = f"{master_key}:{platform}:{spend_cap}:{salt}"
    key_hash = hashlib.sha256(key_material.encode()).hexdigest()
    platform_prefix = "".join([c for c in platform if c.isalpha()])[:6]
    limited_key = f"sk-{platform_prefix}-{spend_cap.replace('.', '')}-{key_hash[:12]}-{salt}"

    if verbose:
        click.echo(f"Generated offline key with format: sk-{platform_prefix}-...", err=True)

    return limited_key


CONSUMERS_DIR = SCRIPT_DIR / "consumers"


def list_consumers():
    """List all available consumers."""
    consumers = []
    if CONSUMERS_DIR.exists():
        for f in CONSUMERS_DIR.glob("*.py"):
            if f.name != "__init__.py" and not f.name.endswith(".disabled"):
                consumers.append(f.stem)
    return consumers


def get_consumer_module(consumer_name):
    """Dynamically load a consumer module."""
    consumer_file = CONSUMERS_DIR / f"{consumer_name}.py"
    if not consumer_file.exists():
        return None
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(consumer_name, consumer_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def handle_send_to(consumer, key, platform, spend_cap, confirm=True):
    """Send the generated key to a consumer."""
    # Try to load consumer module dynamically
    consumer_module = get_consumer_module(consumer)

    if not consumer_module:
        available = list_consumers()
        raise click.ClickException(
            f"Unknown consumer '{consumer}'.\n"
            f"Supported consumers: {', '.join(available) if available else 'none (add one to capit/consumers/)'}"
        )

    if not hasattr(consumer_module, 'send'):
        raise click.ClickException(
            f"Consumer '{consumer}' is missing a 'send' function.\n"
            f"See capit/consumers/example.py for the required interface."
        )

    # Confirm before configuring agent
    if confirm:
        click.echo(f"\n⚠️  This will configure {consumer} with the new limited key.", err=True)
        if not click.confirm("Continue?", default=True, err=True):
            click.echo("Aborted.", err=True)
            return key

    return consumer_module.send(key, platform, spend_cap)


# =============================================================================
# MAIN CLI - Key issuance is the default
# =============================================================================

@click.command(context_settings=dict(
    ignore_unknown_options=False,
    allow_extra_args=False,
    help_option_names=['--help', '-h']
))
@click.argument("platform", required=False)
@click.argument("spend_cap", required=False)
@click.option("--name", "-n", help="Name for the created key")
@click.option("--prefix", "-p", help="Prefix for key organization")
@click.option("--agent", "-a", metavar="AGENT", help="Send key to AI agent (claude, cursor, windsurf)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation when configuring agent")
@click.option("--interactive", "-i", is_flag=True, help="Prompt for master key if not found")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.version_option(version="0.2.0")
@click.pass_context
def main(ctx, platform, spend_cap, name, prefix, agent, yes, interactive, verbose):
    """capit - Cap spending on your AI agents.

\b
Issue a limited key:
  capit openrouter 1.00
  capit openrouter 5.00 --name production --prefix prod
  capit openrouter 1.00 --agent claude
  capit openrouter 1.00 -i

\b
Administration:
  capit --keys list                 List all API keys
  capit --keys list openrouter      List keys from provider
  capit --keys disable openrouter   Disable an API key
  capit --keys enable openrouter    Re-enable a disabled key
  capit --keys delete openrouter    Permanently delete an API key
  capit --keys add openrouter       Add a master key
  capit --keys remove openrouter    Remove a master key (local only)
  capit --platforms                 List available platforms
  capit --stores                    List available stores
  capit --consumers                 List available consumers
"""
    # Check for help flag explicitly
    if '--help' in sys.argv or '-h' in sys.argv:
        click.echo(ctx.get_help())
        ctx.exit(0)

    # Show help if no arguments
    if platform is None and spend_cap is None:
        click.echo(ctx.get_help())
        ctx.exit(0)

    # Require both arguments for key issuance
    if not platform or not spend_cap:
        click.echo("Error: Both PLATFORM and SPEND_CAP are required")
        click.echo("Usage: capit <platform> <spend_cap>")
        click.echo("       capit --help")
        ctx.exit(1)

    # Auto-set prefix based on agent if not explicitly provided
    if agent and not prefix:
        prefix = agent

    try:
        key = do_issue(
            platform, spend_cap,
            name=name, prefix=prefix,
            verbose=verbose,
            interactive=interactive,
            send_to=agent,
            confirm=not yes
        )
        if not agent:
            click.echo(key)
    except click.ClickException as e:
        click.echo(f"Error: {e.format_message()}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Administration commands (-- prefixed, Unix style)
# =============================================================================

@click.group()
def admin():
    """Administration commands."""
    pass


@admin.command("keys")
@click.argument("subcommand", required=False)
@click.argument("args", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def keys_cmd(subcommand, args, verbose):
    """Manage keys.

    capit --keys list                    List all API keys from all providers
    capit --keys list openrouter         List API keys from specific provider
    capit --keys list openrouter capit-*   Filter keys by prefix
    capit --keys disable openrouter <id> Disable an API key
    capit --keys enable openrouter <id>  Re-enable a disabled key
    capit --keys delete openrouter <id>  Permanently delete an API key
    capit --keys add openrouter          Add a master key
    capit --keys remove openrouter       Remove a master key (local only)
    """
    import fnmatch

    if not subcommand:
        click.echo("Usage: capit --keys <command> [args]")
        click.echo("")
        click.echo("Commands:")
        click.echo("  list                List all API keys from all providers")
        click.echo("  list <provider>     List API keys from specific provider")
        click.echo("  list <provider> <prefix>  Filter keys by prefix")
        click.echo("  disable <provider> <key_id>  Disable an API key")
        click.echo("  enable <provider> <key_id>   Re-enable a disabled key")
        click.echo("  delete <provider> <key_id>   Permanently delete an API key")
        click.echo("  add <provider>      Add a master key")
        click.echo("  remove <provider>   Remove a master key (local only)")
        return

    if subcommand == "list":
        if not args:
            # List keys from all registered providers
            lookup = load_master_lookup()
            if not lookup:
                click.echo("No keys registered")
            else:
                for platform, info in lookup.items():
                    store_module = get_store_module(info["store"])
                    master_key = store_module.retrieve_key(platform)
                    if not master_key:
                        continue
                    platform_module = get_platform_module(platform)
                    if not hasattr(platform_module, 'list_keys'):
                        continue
                    try:
                        keys = platform_module.list_keys(master_key)
                        click.echo(f"{platform}:")
                        for key in keys:
                            key_name = key.get("name", key.get("label", "unnamed"))
                            created = key.get("created_at", "")[:10] if key.get("created_at") else ""
                            date_str = f" ({created})" if created else ""
                            click.echo(f"    * {key_name}{date_str}")
                    except Exception:
                        # Skip providers that can't be reached
                        pass
        else:
            # List keys from specific provider
            platform = args[0]
            # Support prefix as positional arg
            prefix = args[1] if len(args) > 1 else None
            ensure_capit_dir()
            lookup = load_master_lookup()
            if platform not in lookup:
                click.echo(f"No master key found for '{platform}'")
                sys.exit(1)
            store_module = get_store_module(lookup[platform]["store"])
            master_key = store_module.retrieve_key(platform)
            platform_module = get_platform_module(platform)
            if not hasattr(platform_module, 'list_keys'):
                click.echo(f"Provider '{platform}' doesn't support listing keys")
                sys.exit(1)
            keys = platform_module.list_keys(master_key)
            # Filter by prefix if specified (glob-style matching)
            if prefix:
                filtered_keys = [k for k in keys if fnmatch.fnmatch(k.get("name", k.get("label", "")), prefix)]
                keys = filtered_keys
            # Print header
            click.echo(f"{'ID':<18} {'NAME':<30} {'LIMIT':>10} {'CREATED':<12} {'STATUS':<10}")
            click.echo("-" * 82)
            for key in keys:
                key_id = key.get("id", key.get("hash", "unknown"))
                key_name = key.get("name", key.get("label", "unnamed"))
                limit_val = key.get("limit")
                if limit_val is not None:
                    limit_str = f"{limit_val:.2f}"
                else:
                    limit_str = "unlimited"
                created = key.get("created_at", "")[:10] if key.get("created_at") else ""
                status = "disabled" if key.get("disabled") else "active"
                click.echo(f"{key_id[:16]:<18} {key_name:<30} {limit_str:>10} {created:<12} {status:<10}")
            click.echo(f"\nTotal: {len(keys)} key(s)")

    elif subcommand == "disable":
        if len(args) < 2:
            click.echo("Usage: capit --keys disable <provider> <key_id>")
            sys.exit(1)
        platform, key_id = args[0], args[1]
        ensure_capit_dir()
        lookup = load_master_lookup()
        if platform not in lookup:
            click.echo(f"No master key found for '{platform}'")
            sys.exit(1)
        store_module = get_store_module(lookup[platform]["store"])
        master_key = store_module.retrieve_key(platform)
        platform_module = get_platform_module(platform)
        if not hasattr(platform_module, 'disable_key'):
            click.echo(f"Provider '{platform}' doesn't support disabling keys")
            sys.exit(1)
        try:
            platform_module.disable_key(master_key, key_id)
            click.echo(f"Key '{key_id}' disabled")
        except Exception as e:
            click.echo(f"Error: {e}")
            sys.exit(1)

    elif subcommand == "enable":
        if len(args) < 2:
            click.echo("Usage: capit --keys enable <provider> <key_id>")
            sys.exit(1)
        platform, key_id = args[0], args[1]
        ensure_capit_dir()
        lookup = load_master_lookup()
        if platform not in lookup:
            click.echo(f"No master key found for '{platform}'")
            sys.exit(1)
        store_module = get_store_module(lookup[platform]["store"])
        master_key = store_module.retrieve_key(platform)
        platform_module = get_platform_module(platform)
        if not hasattr(platform_module, 'enable_key'):
            click.echo(f"Provider '{platform}' doesn't support enabling keys")
            sys.exit(1)
        try:
            platform_module.enable_key(master_key, key_id)
            click.echo(f"Key '{key_id}' enabled")
        except Exception as e:
            click.echo(f"Error: {e}")
            sys.exit(1)

    elif subcommand == "delete":
        if len(args) < 2:
            click.echo("Usage: capit --keys delete <provider> <key_id>")
            sys.exit(1)
        platform, key_id = args[0], args[1]
        ensure_capit_dir()
        lookup = load_master_lookup()
        if platform not in lookup:
            click.echo(f"No master key found for '{platform}'")
            sys.exit(1)
        store_module = get_store_module(lookup[platform]["store"])
        master_key = store_module.retrieve_key(platform)
        platform_module = get_platform_module(platform)
        if not hasattr(platform_module, 'delete_key'):
            click.echo(f"Provider '{platform}' doesn't support deleting keys")
            sys.exit(1)
        try:
            platform_module.delete_key(master_key, key_id)
            click.echo(f"Key '{key_id}' deleted")
        except Exception as e:
            click.echo(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "add":
        if not args:
            click.echo("Usage: capit --keys add <platform>")
            sys.exit(1)
        platform = args[0]
        ensure_capit_dir()
        stores = list_stores()
        default_store = "dotenv" if "dotenv" in stores else stores[0]
        click.echo(f"Store: {default_store}")
        click.echo("Add key:")
        master_key = click.prompt("Key", hide_input=True)
        store_module = get_store_module(default_store)
        store_module.store_key(platform, master_key)
        lookup = load_master_lookup()
        lookup[platform] = {"store": default_store, "added_at": datetime.now().isoformat()}
        save_master_lookup(lookup)
        click.echo("Key added")
    
    elif subcommand == "remove":
        if not args:
            click.echo("Usage: capit --keys remove <platform>")
            sys.exit(1)
        platform = args[0]
        lookup = load_master_lookup()
        if platform not in lookup:
            click.echo(f"No key found for '{platform}'")
            sys.exit(1)
        store_module = get_store_module(lookup[platform]["store"])
        store_module.delete_key(platform)
        del lookup[platform]
        save_master_lookup(lookup)
        click.echo("Success")
    
    else:
        click.echo(f"Unknown command: {subcommand}")
        sys.exit(1)


@admin.command("platforms")
def platforms_cmd():
    """List all available platforms."""
    platforms = list_platforms()
    if not platforms:
        click.echo("No platforms installed")
    else:
        for platform in platforms:
            click.echo(platform)


@admin.command("stores")
def stores_cmd():
    """List all available stores."""
    stores = list_stores()
    if not stores:
        click.echo("No stores installed")
    else:
        for store in stores:
            click.echo(store)


@admin.command("consumers")
def consumers_cmd():
    """List all available consumers."""
    consumers = list_consumers()
    if not consumers:
        click.echo("No consumers installed")
    else:
        for consumer in consumers:
            click.echo(consumer)


@admin.command("enable")
@click.argument("platform")
def enable_cmd(platform):
    """Enable a platform."""
    platform_file = PLATFORMS_DIR / f"{platform}.py"
    disabled_file = PLATFORMS_DIR / f"{platform}.py.disabled"
    if disabled_file.exists():
        disabled_file.rename(platform_file)
        click.echo(f"Platform '{platform}' enabled")
    elif platform_file.exists():
        click.echo(f"Platform '{platform}' is already enabled")
    else:
        click.echo(f"Platform '{platform}' not found")
        sys.exit(1)


@admin.command("disable")
@click.argument("platform")
def disable_cmd(platform):
    """Disable a platform."""
    platform_file = PLATFORMS_DIR / f"{platform}.py"
    disabled_file = PLATFORMS_DIR / f"{platform}.py.disabled"
    if platform_file.exists():
        platform_file.rename(disabled_file)
        click.echo(f"Platform '{platform}' disabled")
    elif disabled_file.exists():
        click.echo(f"Platform '{platform}' is already disabled")
    else:
        click.echo(f"Platform '{platform}' not found")
        sys.exit(1)


def cli():
    """Main entry point."""
    # Check for --help/-h first - always show help
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        main()
        return

    # Check for -- prefixed admin commands and translate them
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Map --command to command
        if arg.startswith("--") and len(arg) > 2:
            sys.argv[1] = arg[2:]  # Remove -- prefix

        # Check if it's an admin command
        admin_commands = {"keys", "platforms", "stores", "consumers", "enable", "disable"}
        if sys.argv[1] in admin_commands:
            admin()
            return

    main()


if __name__ == "__main__":
    cli()
