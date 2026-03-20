# capit Agents

Agents are AI tools and assistants that capit can automatically configure with capped API keys.

When you run `capit openrouter 5.00 --agent claude -y`, capit:
1. Creates a limited key with OpenRouter
2. Writes it to the agent's config file
3. You're ready to go

## Built-in Agents

| Agent | Config File | Command |
|-------|-------------|---------|
| **claude** | `~/.claude/.credentials.json` | `capit openrouter 5.00 --agent claude -y` |
| **cursor** | `~/.config/Cursor/User/settings.json` | `capit openrouter 10.00 --agent cursor -y` |
| **windsurf** | `~/.config/Windsurf/User/settings.json` | `capit openrouter 5.00 --agent windsurf -y` |
| **openclaw** | `~/.openclaw/secrets.json` + `openclaw.json` | `capit openrouter 5.00 --agent openclaw -y` |

## Output Format

All agents use the same clean output:

```bash
$ capit openrouter 5.00 --agent claude -y
$5.00 openrouter key installed into claude
```

## Adding a Custom Agent

### Option 1: Ask Claude

Use the agent-creator skill:

```
Add a new agent for my-agent that writes the API key to ~/.myagent/config.json
```

See [skills/agent-creator.md](../skills/agent-creator.md) for details.

### Option 2: Manual

1. Copy the template:
   ```bash
   cp capit/agents/example.py capit/agents/myagent.py
   ```

2. Edit `capit/agents/myagent.py`:
   ```python
   """MyAgent agent for capit."""

   import json
   from pathlib import Path
   import click


   def send(key: str, platform: str, spend_cap: str) -> str:
       """Configure API key for MyAgent."""
       config_path = Path.home() / ".myagent" / "config.json"
       config_path.parent.mkdir(parents=True, exist_ok=True)

       if config_path.exists():
           with open(config_path, "r") as f:
               config = json.load(f)
       else:
           config = {}

       config["api_key"] = key

       with open(config_path, "w") as f:
           json.dump(config, f, indent=2)

       click.echo(f"${spend_cap} {platform} key installed into myagent")
       return key
   ```

3. Test it:
   ```bash
   capit --agents  # Should list myagent
   capit openrouter 5.00 --agent myagent -y
   ```

## Agent Interface

Every agent must implement:

```python
def send(key: str, platform: str, spend_cap: str) -> str:
    """Configure the API key for this agent.

    Args:
        key: The generated limited API key
        platform: The platform name (e.g., "openrouter")
        spend_cap: The spending cap (e.g., "5.00")

    Returns:
        The key (for potential chaining)

    Output:
        Must print: f"${spend_cap} {platform} key installed into <agent>"
    """
```

## Listing Agents

```bash
capit --agents
# claude
# cursor
# windsurf
# openclaw
# example
# myagent
```
