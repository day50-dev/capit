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


AGENTS_DIR = SCRIPT_DIR / "agents"


def list_agents():
    """List all available agents."""
    agents = []
    if AGENTS_DIR.exists():
        for f in AGENTS_DIR.glob("*.py"):
            if f.name != "__init__.py" and not f.name.endswith(".disabled"):
                agents.append(f.stem)
    return agents


def get_agent_module(agent_name):
    """Dynamically load an agent module."""
    agent_file = AGENTS_DIR / f"{agent_name}.py"
    if not agent_file.exists():
        return None

    import importlib.util
    spec = importlib.util.spec_from_file_location(agent_name, agent_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def handle_send_to(agent, key, platform, spend_cap, confirm=True):
    """Send the generated key to an agent."""
    # Try to load agent module dynamically
    agent_module = get_agent_module(agent)

    if not agent_module:
        available = list_agents()
        raise click.ClickException(
            f"Unknown agent '{agent}'.\n"
            f"Supported agents: {', '.join(available) if available else 'none (add one to capit/agents/)'}"
        )

    if not hasattr(agent_module, 'send'):
        raise click.ClickException(
            f"Agent '{agent}' is missing a 'send' function.\n"
            f"See capit/agents/example.py for the required interface."
        )

    # Confirm before configuring agent
    if confirm:
        click.echo(f"\n⚠️  This will configure {agent} with the new limited key.", err=True)
        if not click.confirm("Continue?", default=True, err=True):
            click.echo("Aborted.", err=True)
            return key

    return agent_module.send(key, platform, spend_cap)


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
@click.pass_context
def main(ctx, platform, spend_cap, name, prefix, agent, yes, interactive, verbose):
    """capit - Cap spending on your AI agents.

\b
Issue a limited key:
  capit openrouter 1.00
  capit openrouter 5.00 --name prod
  capit openrouter 1.00 --agent claude
  capit openrouter 1.00 -i

\b
Administration:
  capit --keys list               List all keys
  capit --keys list openrouter    List keys from provider
  capit --keys disable <pattern>  Disable key(s)
  capit --keys enable <pattern>   Re-enable disabled key(s)
  capit --keys delete <pattern>   Permanently delete key(s)
  capit --platforms               List platforms
  capit --platforms add           Add a master key
  capit --platforms remove        Remove a master key
  capit --stores                  List available stores
  capit --agents                  List available agents
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


def _parse_key_pattern(pattern, lookup):
    """Parse a key pattern and return matching keys across providers.
    
    Patterns supported:
    - "name" - exact match or glob across all providers
    - "provider/name" - exact match or glob on specific provider
    - "name*" or "*name" or "name*pattern" - glob matching
    
    Returns list of tuples: (platform, key_id, key_data)
    """
    import fnmatch
    
    matches = []
    
    # Check if pattern includes provider prefix
    if "/" in pattern:
        parts = pattern.split("/", 1)
        provider_filter = parts[0]
        name_pattern = parts[1]
    else:
        provider_filter = None
        name_pattern = pattern
    
    # Determine which providers to search
    providers_to_search = []
    if provider_filter:
        if provider_filter in lookup:
            providers_to_search = [provider_filter]
        else:
            return []  # Provider not found
    else:
        providers_to_search = list(lookup.keys())
    
    # Search each provider
    for platform in providers_to_search:
        info = lookup[platform]
        store_module = get_store_module(info["store"])
        master_key = store_module.retrieve_key(platform)
        if not master_key:
            continue
        platform_module = get_platform_module(platform)
        if not hasattr(platform_module, 'list_keys'):
            continue
        try:
            keys = platform_module.list_keys(master_key)
            for key in keys:
                key_name = key.get("name", key.get("label", ""))
                # Check if name matches pattern (glob or exact)
                if fnmatch.fnmatch(key_name, name_pattern):
                    # Get key ID - try multiple field names
                    key_id = key.get("id") or key.get("hash") or key.get("key_id")
                    if key_id:
                        matches.append((platform, key_id, key))
        except Exception:
            continue
    
    return matches


def _find_key_by_name(platform_module, master_key, key_name):
    """Find a key by name and return its ID."""
    keys = platform_module.list_keys(master_key)
    for key in keys:
        name = key.get("name", key.get("label", ""))
        if name == key_name:
            return key.get("id"), key
    return None, None


@admin.command("keys", context_settings=dict(
    ignore_unknown_options=True,
    help_option_names=[]  # Disable click's built-in --help handling
))
@click.argument("subcommand", required=False)
@click.argument("args", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def keys_cmd(subcommand, args, verbose):
    """Manage keys."""
    import fnmatch

    # Check for --help explicitly to show nice help screen
    if "--help" in sys.argv or "-h" in sys.argv:
        click.echo("Usage: capit --keys <command> [args]")
        click.echo("")
        click.echo("Commands:")
        click.echo("  list                     List all keys from all providers")
        click.echo("  list <provider>          List keys from specific provider")
        click.echo("  list <provider> <prefix> Filter keys by prefix")
        click.echo("  disable <pattern>        Disable key(s)")
        click.echo("  enable <pattern>         Re-enable disabled key(s)")
        click.echo("  delete <pattern>         Permanently delete key(s)")
        click.echo("")
        click.echo("Patterns:")
        click.echo("  name              Exact match or glob across all providers")
        click.echo("  provider/name     Match on specific provider")
        click.echo("  name*             Glob pattern (e.g., 'capit-*')")
        click.echo("")
        click.echo("Examples:")
        click.echo("  capit --keys list")
        click.echo("  capit --keys list openrouter")
        click.echo("  capit --keys disable claude-71ad2519")
        click.echo("  capit --keys disable 'capit-*'")
        click.echo("  capit --keys disable 'openrouter/capit-*'")
        sys.exit(0)

    # If no subcommand, default to list all
    if subcommand is None:
        subcommand = "list"
        args = tuple()

    if subcommand == "list":
        if not args:
            # List keys from all registered providers with namespaced names
            lookup = load_master_lookup()
            if not lookup:
                click.echo("No keys registered")
            else:
                all_keys = []
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
                        for key in keys:
                            key_with_provider = {
                                **key,
                                "_provider": platform,
                                "_namespaced_name": f"{platform}/{key.get('name', key.get('label', 'unnamed'))}"
                            }
                            all_keys.append(key_with_provider)
                    except Exception:
                        # Skip providers that can't be reached
                        pass
                # Sort by namespaced name
                all_keys = sorted(all_keys, key=lambda k: k.get("_namespaced_name", "").lower())
                # Print header with unicode box drawing
                click.echo(f"{'NAME':<40} {'LIMIT':>10} {'CREATED':<12} {'STATUS':<10}")
                click.echo("─" * 76)
                for key in all_keys:
                    key_name = key.get("_namespaced_name", "unknown")
                    limit_val = key.get("limit")
                    if limit_val is not None:
                        limit_str = f"{limit_val:.2f}"
                    else:
                        limit_str = "unlimited"
                    created = key.get("created_at", "")[:10] if key.get("created_at") else ""
                    status = "disabled" if key.get("disabled") else "active"
                    # Color status
                    if status == "active":
                        status_display = click.style(status, fg="green")
                    else:
                        status_display = click.style(status, fg="yellow")
                    click.echo(f"{key_name:<40} {limit_str:>10} {created:<12} {status_display:<10}")
                click.echo(f"\nTotal: {len(all_keys)} key(s)")
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
            # Print header with unicode box drawing
            click.echo(f"{'NAME':<35} {'LIMIT':>10} {'CREATED':<12} {'STATUS':<10}")
            click.echo("─" * 71)
            # Sort by name for intuitive grouping
            keys = sorted(keys, key=lambda k: k.get("name", k.get("label", "")).lower())
            for key in keys:
                key_name = key.get("name", key.get("label", "unnamed"))
                limit_val = key.get("limit")
                if limit_val is not None:
                    limit_str = f"{limit_val:.2f}"
                else:
                    limit_str = "unlimited"
                created = key.get("created_at", "")[:10] if key.get("created_at") else ""
                status = "disabled" if key.get("disabled") else "active"
                # Color status
                if status == "active":
                    status_display = click.style(status, fg="green")
                else:
                    status_display = click.style(status, fg="yellow")
                click.echo(f"{key_name:<35} {limit_str:>10} {created:<12} {status_display:<10}")
            click.echo(f"\nTotal: {len(keys)} key(s)")
        return

    if not args:
        click.echo("Usage: capit --keys <command> [args]")
        click.echo("")
        click.echo("Commands:")
        click.echo("  list                     List all keys from all providers")
        click.echo("  list <provider>          List keys from specific provider")
        click.echo("  list <provider> <prefix> Filter keys by prefix")
        click.echo("  disable <pattern>        Disable key(s)")
        click.echo("  enable <pattern>         Re-enable disabled key(s)")
        click.echo("  delete <pattern>         Permanently delete key(s)")
        click.echo("")
        click.echo("Patterns:")
        click.echo("  name              Exact match or glob across all providers")
        click.echo("  provider/name     Match on specific provider")
        click.echo("  name*             Glob pattern (e.g., 'capit-*')")
        click.echo("")
        click.echo("Examples:")
        click.echo("  capit --keys disable claude-71ad2519")
        click.echo("  capit --keys disable 'capit-*'")
        click.echo("  capit --keys disable 'openrouter/capit-*'")
        return

    elif subcommand == "disable":
        if not args:
            click.echo("Usage: capit --keys disable <pattern>")
            sys.exit(1)
        pattern = args[0]
        ensure_capit_dir()
        lookup = load_master_lookup()
        matches = _parse_key_pattern(pattern, lookup)
        if not matches:
            click.echo(f"No keys matching '{pattern}'")
            sys.exit(1)
        disabled_count = 0
        for platform, key_id, key_data in matches:
            key_name = key_data.get("name", key_data.get("label", ""))
            store_module = get_store_module(lookup[platform]["store"])
            master_key = store_module.retrieve_key(platform)
            platform_module = get_platform_module(platform)
            if not hasattr(platform_module, 'disable_key'):
                click.echo(f"Provider '{platform}' doesn't support disabling keys")
                continue
            try:
                platform_module.disable_key(master_key, key_id)
                click.echo(f"Disabled: {platform}/{key_name}")
                disabled_count += 1
            except Exception as e:
                click.echo(f"Error disabling {platform}/{key_name}: {e}")
        click.echo(f"\nDisabled {disabled_count} key(s)")
        return

    elif subcommand == "enable":
        if not args:
            click.echo("Usage: capit --keys enable <pattern>")
            sys.exit(1)
        pattern = args[0]
        ensure_capit_dir()
        lookup = load_master_lookup()
        matches = _parse_key_pattern(pattern, lookup)
        if not matches:
            click.echo(f"No keys matching '{pattern}'")
            sys.exit(1)
        enabled_count = 0
        for platform, key_id, key_data in matches:
            key_name = key_data.get("name", key_data.get("label", ""))
            store_module = get_store_module(lookup[platform]["store"])
            master_key = store_module.retrieve_key(platform)
            platform_module = get_platform_module(platform)
            if not hasattr(platform_module, 'enable_key'):
                click.echo(f"Provider '{platform}' doesn't support enabling keys")
                continue
            try:
                platform_module.enable_key(master_key, key_id)
                click.echo(f"Enabled: {platform}/{key_name}")
                enabled_count += 1
            except Exception as e:
                click.echo(f"Error enabling {platform}/{key_name}: {e}")
        click.echo(f"\nEnabled {enabled_count} key(s)")
        return

    elif subcommand == "delete":
        if not args:
            click.echo("Usage: capit --keys delete <pattern>")
            sys.exit(1)
        pattern = args[0]
        ensure_capit_dir()
        lookup = load_master_lookup()
        matches = _parse_key_pattern(pattern, lookup)
        if not matches:
            click.echo(f"No keys matching '{pattern}'")
            sys.exit(1)
        deleted_count = 0
        for platform, key_id, key_data in matches:
            key_name = key_data.get("name", key_data.get("label", ""))
            store_module = get_store_module(lookup[platform]["store"])
            master_key = store_module.retrieve_key(platform)
            platform_module = get_platform_module(platform)
            if not hasattr(platform_module, 'delete_key'):
                click.echo(f"Provider '{platform}' doesn't support deleting keys")
                continue
            try:
                platform_module.delete_key(master_key, key_id)
                click.echo(f"Deleted: {platform}/{key_name}")
                deleted_count += 1
            except Exception as e:
                click.echo(f"Error deleting {platform}/{key_name}: {e}")
        click.echo(f"\nDeleted {deleted_count} key(s)")
        return

    else:
        click.echo(f"Unknown command: {subcommand}")
        sys.exit(1)


@admin.command("platforms")
@click.argument("subcommand", required=False)
@click.argument("args", nargs=-1)
def platforms_cmd(subcommand, args):
    """Manage platforms and master keys."""
    if subcommand is None:
        platforms = list_platforms()
        if not platforms:
            click.echo("No platforms installed")
        else:
            click.echo("Usage: capit --platforms <command> [args]")
            click.echo("")
            click.echo("Commands:")
            click.echo("  list    List available platforms")
            click.echo("  add     Add a master key")
            click.echo("  remove  Remove a master key")
            click.echo("")
            click.echo("Platforms:")
            for platform in platforms:
                click.echo(f"  {platform}")
        return

    if subcommand == "list":
        platforms = list_platforms()
        if not platforms:
            click.echo("No platforms installed")
        else:
            for platform in platforms:
                click.echo(platform)
        return

    if subcommand == "add":
        if not args:
            click.echo("Usage: capit --platforms add <platform>")
            sys.exit(1)
        platform = args[0]
        ensure_capit_dir()
        stores = list_stores()
        default_store = "dotenv" if "dotenv" in stores else stores[0]
        click.echo(f"Store: {default_store}")
        click.echo("Add master key:")
        master_key = click.prompt("Key", hide_input=True)
        store_module = get_store_module(default_store)
        store_module.store_key(platform, master_key)
        lookup = load_master_lookup()
        lookup[platform] = {"store": default_store, "added_at": datetime.now().isoformat()}
        save_master_lookup(lookup)
        click.echo("Master key added")
        return

    if subcommand == "remove":
        if not args:
            click.echo("Usage: capit --platforms remove <platform>")
            sys.exit(1)
        platform = args[0]
        lookup = load_master_lookup()
        if platform not in lookup:
            click.echo(f"No master key found for '{platform}'")
            sys.exit(1)
        store_module = get_store_module(lookup[platform]["store"])
        store_module.delete_key(platform)
        del lookup[platform]
        save_master_lookup(lookup)
        click.echo("Master key removed")
        return

    click.echo(f"Unknown command: {subcommand}")
    sys.exit(1)


@admin.command("stores")
def stores_cmd():
    """List all available stores."""
    stores = list_stores()
    if not stores:
        click.echo("No stores installed")
    else:
        for store in stores:
            click.echo(store)


@admin.command("agents")
def agents_cmd():
    """List all available agents."""
    consumers = list_consumers()
    if not consumers:
        click.echo("No agents installed")
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
    # Check for --help/-h/--version first - always handle these
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        main()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        from importlib.metadata import version
        click.echo(version("capit"))
        return

    # Check for -- prefixed admin commands and translate them
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Map --command to command
        if arg.startswith("--") and len(arg) > 2:
            sys.argv[1] = arg[2:]  # Remove -- prefix

        # Check if it's an admin command
        admin_commands = {"keys", "platforms", "stores", "agents", "enable", "disable"}
        if sys.argv[1] in admin_commands:
            admin()
            return

    main()


if __name__ == "__main__":
    cli()
