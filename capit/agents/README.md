# capit Agents

Agents are AI tools and assistants that capit can automatically configure with capped API keys.

When you run `capit openrouter 5.00 --agent claude`, capit:
1. Shows a diff of what will change (with `<new key>` placeholder)
2. Asks for confirmation
3. Creates the limited key only after you confirm
4. Updates the agent's config file
5. Backs up the old configuration

## Built-in Agents

| Agent | Config File | Command |
|-------|-------------|---------|
| **claude** | `~/.claude/.credentials.json` | `capit openrouter 5.00 --agent claude` |
| **cursor** | `~/.config/Cursor/User/settings.json` | `capit openrouter 10.00 --agent cursor` |
| **windsurf** | `~/.config/Windsurf/User/settings.json` | `capit openrouter 5.00 --agent windsurf` |
| **openclaw** | `~/.openclaw/secrets.json` + `openclaw.json` | `capit openrouter 5.00 --agent openclaw` |
| **opencode** | `~/.local/share/opencode/auth.json` | `capit openrouter 5.00 --agent opencode` |

## Output Format

All agents use the same clean output:

```bash
$ capit openrouter 5.00 --agent claude

Configure claude with a new openrouter key (limit: $5.00)?
Changes:
--- /tmp/capit-current-xxx.json
+++ /tmp/capit-staged-yyy.json
@@ -1,3 +1,3 @@
 {
-  "api_key": "sk-or-v1-oldkey..."
+  "api_key": "<new key>"
 }

Continue? [Y/n]: y
$5.00 openrouter key installed into claude
Old configuration backed up to /tmp/capit-abc123/.credentials.json
```

## Adding a Custom Agent

### Option 1: Ask Claude

Use the agent-creator skill:

```
Add a new agent for my-agent that writes the API key to ~/.myagent/config.json
```

See [skills/agent-creator.md](../skills/agent-creator.md) for details.

### Option 2: Manual

#### Simple Agent (single key field)

For agents with a simple config like `{"api_key": "..."}`:

```python
"""MyAgent agent for capit."""

from pathlib import Path
from capit.agents.lib import show_json_diff, install_key


def get_config_path() -> Path:
    """Get the config file path for this agent."""
    return Path.home() / ".myagent" / "config.json"


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation."""
    return show_json_diff(
        get_config_path(),
        "api_key",
        "<new key>",
        agent,
        platform,
        spend_cap
    )


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Send key to MyAgent by updating config file."""
    return install_key(
        get_config_path(),
        "api_key",
        key,
        platform,
        "myagent",
        spend_cap
    )
```

#### Nested Key Agent

For agents with nested config like `{"openrouter": {"key": "..."}}`:

```python
"""MyAgent agent for capit."""

from pathlib import Path
from capit.agents.lib import show_json_diff, install_key


def get_config_path() -> Path:
    return Path.home() / ".myagent" / "config.json"


def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    return show_json_diff(
        get_config_path(),
        f"{platform}.key",  # e.g., "openrouter.key"
        "<new key>",
        agent,
        platform,
        spend_cap
    )


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    return install_key(
        get_config_path(),
        f"{platform}.key",
        key,
        platform,
        "myagent",
        spend_cap
    )
```

#### Complex Agent (multiple files)

For agents that need to update multiple config files (like OpenClaw), see `capit/agents/openclaw.py` for a reference implementation.

## Agent Interface

Every agent must implement:

```python
def show_diff(platform: str, spend_cap: str, agent: str) -> bool:
    """Show diff of changes and ask for confirmation.
    
    Returns True if user confirmed, False if aborted.
    """


def send(key: str, platform: str, spend_cap: str, confirm: bool = True) -> str:
    """Configure the API key for this agent.
    
    Args:
        key: The generated limited API key
        platform: The platform name (e.g., "openrouter")
        spend_cap: The spending cap (e.g., "5.00")
        confirm: Ignored (confirmation already handled by show_diff)
    
    Returns:
        The key (for potential chaining)
    
    Output:
        Must print: f"${spend_cap} {platform} key installed into <agent>"
        Should also print backup location if backup was created.
    """
```

## Library Functions

The `capit.agents.lib` module provides helper functions:

### `show_json_diff()`

Shows a staged diff with `<new key>` placeholder and asks for confirmation.

```python
show_json_diff(
    config_path=Path.home() / ".myagent" / "config.json",
    key_path="api_key",  # or "openrouter.key" for nested
    new_value="<new key>",
    agent="myagent",
    platform="openrouter",
    spend_cap="5.00"
)
```

### `install_key()`

Installs the key to a JSON config file with backup.

```python
install_key(
    config_path=Path.home() / ".myagent" / "config.json",
    key_path="api_key",
    key_value="sk-or-v1-...",
    platform="openrouter",
    agent="myagent",
    spend_cap="5.00",
    mode=0o600  # file permissions
)
```

## Listing Agents

```bash
capit --agents
# claude
# cursor
# windsurf
# openclaw
# opencode
# example
```

## Testing

After creating an agent:

```bash
capit --agents  # Should list your agent
capit openrouter 5.00 --agent myagent  # Test it
```
