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


def do_issue(platform, spend_cap, name=None, prefix=None, verbose=False, interactive=False, send_to=None):
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
                return handle_send_to(send_to, limited_key, platform, spend_cap)
            
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


def handle_send_to(consumer, key, platform, spend_cap):
    """Send the generated key to a consumer (e.g., claude-code)."""
    consumer_handlers = {
        "claude": send_to_claude,
        "claude-code": send_to_claude,
        "cursor": send_to_cursor,
        "windsurf": send_to_windsurf,
    }
    
    handler = consumer_handlers.get(consumer.lower())
    if not handler:
        raise click.ClickException(
            f"Unknown consumer '{consumer}'.\n"
            f"Supported consumers: {', '.join(consumer_handlers.keys())}"
        )
    
    return handler(key, platform, spend_cap)


def send_to_claude(key, platform, spend_cap):
    """Send key to Claude by setting environment variable and providing instructions."""
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with Claude, run:", err=True)
    click.echo(f"  export OPENROUTER_API_KEY={key}", err=True)
    click.echo(f"\nOr pipe to claude-code:", err=True)
    click.echo(f"  OPENROUTER_API_KEY={key} claude", err=True)
    return key


def send_to_cursor(key, platform, spend_cap):
    """Send key to Cursor IDE."""
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with Cursor:", err=True)
    click.echo(f"  1. Open Cursor Settings > AI > API Keys", err=True)
    click.echo(f"  2. Add this key to OpenRouter", err=True)
    return key


def send_to_windsurf(key, platform, spend_cap):
    """Send key to Windsurf IDE."""
    click.echo(f"\n🔑 Generated limited key for {platform} (${spend_cap} cap)", err=True)
    click.echo(f"Key: {key}", err=True)
    click.echo(f"\nTo use with Windsurf:", err=True)
    click.echo(f"  1. Open Windsurf Settings > AI", err=True)
    click.echo(f"  2. Add this key to OpenRouter", err=True)
    return key


# =============================================================================
# MAIN CLI - Key issuance is the default
# =============================================================================

@click.command(context_settings=dict(
    ignore_unknown_options=False,
    allow_extra_args=False,
))
@click.argument("platform")
@click.argument("spend_cap")
@click.option("--name", "-n", help="Name for the created key")
@click.option("--prefix", "-p", help="Prefix for key organization")
@click.option("--send-to", "-s", help="Send key to consumer (claude, cursor, windsurf)")
@click.option("--interactive", "-i", is_flag=True, help="Prompt for master key if not found")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.version_option(version="0.2.0")
def main(platform, spend_cap, name, prefix, send_to, interactive, verbose):
    """capit - Issue authentication keys with spending caps.
    
    Issue a limited key:
        capit openrouter 1.00
        capit openrouter 5.00 --name production --prefix prod
        capit openrouter 1.00 --send-to claude
        capit openrouter 1.00 -i  # Prompt for key if not found
    
    Administration:
        capit --keys list           List master keys
        capit --keys remote openrouter  List API keys from platform  
        capit --keys delete openrouter <id>  Revoke an API key
        capit --keys add openrouter  Add a master key
        capit --keys remove openrouter  Remove a master key
        capit --platforms           List available platforms
        capit --stores              List available stores
    """
    try:
        key = do_issue(
            platform, spend_cap, 
            name=name, prefix=prefix, 
            verbose=verbose, 
            interactive=interactive,
            send_to=send_to
        )
        if not send_to:
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


@admin.command("--keys")
@click.argument("subcommand", required=False)
@click.argument("args", nargs=-1)
@click.option("-r", "--remote", is_flag=True, help="Remote operation (list/delete API keys)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def keys_cmd(subcommand, args, remote, verbose):
    """Manage keys.
    
    capit --keys list                    List master keys
    capit --keys list -r openrouter      List API keys from platform
    capit --keys delete openrouter <id>  Delete an API key
    capit --keys add openrouter          Add a master key
    capit --keys remove openrouter       Remove a master key
    """
    if not subcommand:
        click.echo("Usage: capit --keys <command> [args]")
        click.echo("")
        click.echo("Commands:")
        click.echo("  list                List master keys")
        click.echo("  list -r <platform>  List API keys from platform")
        click.echo("  delete <platform> <key_id>  Delete an API key")
        click.echo("  add <platform>      Add a master key")
        click.echo("  remove <platform>   Remove a master key")
        return
    
    if subcommand == "list":
        if remote:
            if not args:
                click.echo("Error: Platform required for remote listing")
                click.echo("Usage: capit --keys list -r <platform>")
                sys.exit(1)
            platform = args[0]
            ensure_capit_dir()
            lookup = load_master_lookup()
            if platform not in lookup:
                click.echo(f"No master key found for '{platform}'")
                sys.exit(1)
            store_module = get_store_module(lookup[platform]["store"])
            master_key = store_module.retrieve_key(platform)
            platform_module = get_platform_module(platform)
            if not hasattr(platform_module, 'list_keys'):
                click.echo(f"Platform '{platform}' doesn't support listing keys")
                sys.exit(1)
            keys = platform_module.list_keys(master_key)
            click.echo(f"Keys for {platform}:")
            for key in keys:
                key_id = key.get("id", key.get("hash", "unknown"))
                key_name = key.get("name", key.get("label", "unnamed"))
                limit_val = key.get("limit")
                limit_str = f"${limit_val}" if limit_val else "unlimited"
                created = key.get("created_at", "")[:10] if key.get("created_at") else ""
                status = "disabled" if key.get("disabled") else "active"
                click.echo(f"  {key_id[:16]}...  {key_name:30}  {limit_str:12}  {created}  [{status}]")
            click.echo(f"\nTotal: {len(keys)} key(s)")
        else:
            lookup = load_master_lookup()
            if not lookup:
                click.echo("No keys registered")
            else:
                for platform, info in lookup.items():
                    click.echo(f"{platform} | {info['store']}")
    
    elif subcommand == "delete":
        if len(args) < 2:
            click.echo("Usage: capit --keys delete <platform> <key_id>")
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
            click.echo(f"Platform '{platform}' doesn't support deleting keys")
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


@admin.command("--platforms")
def platforms_cmd():
    """List all available platforms."""
    platforms = list_platforms()
    if not platforms:
        click.echo("No platforms installed")
    else:
        for platform in platforms:
            click.echo(platform)


@admin.command("--stores")
def stores_cmd():
    """List all available stores."""
    stores = list_stores()
    if not stores:
        click.echo("No stores installed")
    else:
        for store in stores:
            click.echo(store)


@admin.command("--enable")
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


@admin.command("--disable")
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
    # Check for -- prefixed admin commands
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--keys", "--platforms", "--stores", "--enable", "--disable"):
            admin()
            return
    main()


if __name__ == "__main__":
    cli()
