---
name: capit-agent-creator
description: Create new AI agent integrations for capit. Use when users want to add support for a new AI coding assistant, IDE, or tool that needs API key configuration.
---

# capit Agent Creator

This skill helps you create new agents for [capit](https://github.com/capit/capit) - a tool that issues capped API keys for AI agents.

## Quick Start

Ask me to create an agent:

```
Add a new agent for my-agent that writes the API key to ~/.myagent/config.json
```

I'll create a properly structured agent using capit's base classes.

## Agent Architecture

capit agents use an object-oriented approach with base classes:

- **`SimpleAgent`** - For agents with simple JSON config (most common)
- **`Agent`** - For agents needing custom logic (multiple files, special formats)

## Creating a Simple Agent

Most agents just need to inherit from `SimpleAgent`:

```python
"""<Agent Name> agent for capit."""

from pathlib import Path
from capit.agents.base import SimpleAgent


class <AgentName>Agent(SimpleAgent):
    """<Agent Name> integration."""

    name = "<agent-name>"
    config_path = Path.home() / ".<agent>" / "config.json"
    key_path = "api_key"  # or use get_key_path() for dynamic


# Module-level functions for backwards compatibility
_agent = <AgentName>Agent()
show_diff = _agent.show_diff
send = _agent.send
get_config_path = _agent.get_config_path
```

## Creating a Complex Agent

For agents with multiple config files or custom logic:

```python
"""<Agent Name> agent for capit."""

from pathlib import Path
from capit.agents.base import Agent, create_backups


class <AgentName>Agent(Agent):
    """<Agent Name> integration - manages multiple config files."""

    name = "<agent-name>"

    def get_config_path(self) -> Path:
        return Path.home() / ".<agent>" / "config.json"

    def get_config_files(self) -> list:
        """Return multiple files for backup."""
        return [
            (self.get_secrets_path(), "secrets.json"),
            (self.get_config_path(), "config.json")
        ]

    def _prepare_config(self, config: dict, key: str, platform: str) -> dict:
        """Custom config preparation."""
        config[platform] = {"type": "api", "key": key}
        return config


# Module-level functions for backwards compatibility
_agent = <AgentName>Agent()
show_diff = _agent.show_diff
send = _agent.send
get_config_path = _agent.get_config_path
```

## Step-by-Step Process

### 1. Identify the Agent's Config

Determine:
- Config file path (e.g., `~/.claude/.credentials.json`)
- Key field name (e.g., `api_key` or `openrouter.apiKey`)
- Config format (JSON, YAML, etc.)
- Whether multiple files need updating

### 2. Create the Agent File

Create `capit/agents/<agent-name>.py` with:
- Docstring describing the agent
- Class inheriting from `SimpleAgent` or `Agent`
- Required class attributes or method overrides
- Module-level exports for backwards compatibility

### 3. Test the Agent

```bash
# Verify agent is listed
capit --agents

# Test with a small cap
capit openrouter 1.00 --agent <agent-name> -y
```

## Examples

### Example 1: Simple JSON Config

```python
"""Cursor agent for capit."""

from pathlib import Path
from capit.agents.base import SimpleAgent


class CursorAgent(SimpleAgent):
    """Cursor IDE integration."""

    name = "cursor"
    key_path = "openrouter.apiKey"

    def get_config_path(self) -> Path:
        return Path.home() / ".config" / "Cursor" / "User" / "settings.json"


_agent = CursorAgent()
show_diff = _agent.show_diff
send = _agent.send
get_settings_path = _agent.get_config_path
```

### Example 2: Nested Key with Dynamic Platform

```python
"""Windsurf agent for capit."""

from pathlib import Path
from capit.agents.base import SimpleAgent


class WindsurfAgent(SimpleAgent):
    """Windsurf IDE integration."""

    name = "windsurf"

    def get_config_path(self) -> Path:
        return Path.home() / ".config" / "Windsurf" / "User" / "settings.json"

    def get_key_path(self, platform: str = None) -> str:
        return f"{platform}.apiKey"


_agent = WindsurfAgent()
show_diff = _agent.show_diff
send = _agent.send
get_settings_path = _agent.get_config_path
```

### Example 3: Multiple Config Files

See `capit/agents/openclaw.py` for a reference implementation managing two files.

## Key Path Patterns

| Pattern | Example | Use Case |
|---------|---------|----------|
| Simple | `api_key` | Direct key storage |
| Nested | `openrouter.apiKey` | Provider-specific keys |
| Dynamic | `f"{platform}.key"` | Multiple providers |

## Backup System

All agents automatically:
- Create timestamped backups before modifying configs
- Store backups in `/tmp/capit-{agent}-{random}/`
- Print backup location after installation

## Output Format

Agents must print:
```
$<spend_cap> <platform> key installed into <agent>
Old configuration backed up to /tmp/capit-<agent>-<random>/<file>
```

## Testing Checklist

- [ ] Agent file created in `capit/agents/`
- [ ] Class inherits from `SimpleAgent` or `Agent`
- [ ] `name` attribute set
- [ ] `get_config_path()` returns correct path
- [ ] Module-level exports defined
- [ ] `capit --agents` lists the agent
- [ ] `capit openrouter 1.00 --agent <name> -y` succeeds
- [ ] Config file updated correctly
- [ ] Backup created

## Common Pitfalls

1. **Forgetting module exports** - Always add `_agent`, `show_diff`, `send`
2. **Wrong key path** - Check the agent's actual config structure
3. **Missing parents** - Use `mkdir(parents=True, exist_ok=True)`
4. **No error handling** - Handle `JSONDecodeError` for corrupted configs

## Related Files

- `capit/agents/base.py` - Base classes and utilities
- `capit/agents/claude.py` - Simple agent example
- `capit/agents/openclaw.py` - Complex agent example
