<p align="center">
<img width="500" height="187" alt="capit_500" src="https://github.com/user-attachments/assets/db22c959-ffee-4540-9108-2928e9c73f70" />
<br/>
<a href=https://pypi.org/project/capit><img src=https://badge.fury.io/py/capit.svg/></a>
<br/><strong>Budget per-agent, per-provider, as little or as much as you want</strong>
</p>

```bash
$ uvx capit openrouter 5.00 --agent openclaw
$5.00 openrouter key installed into openclaw
Old configuration backed up to /tmp/capit-openclaw-no22x7b1
```

That's it. Openclaw now has a capped API key. If it goes rogue, it can only cost you $5.

---

## Install

```bash
uv tool install capit
```

## Usage

### Give an agent a budget

```bash
# Claude Code - $5 cap
capit openrouter 5.00 --agent claude

# Cursor - $10 cap
capit openrouter 10.00 --agent cursor

# Windsurf - $5 cap
capit openrouter 5.00 --agent windsurf

# OpenClaw - $5 cap
capit openrouter 5.00 --agent openclaw
```

Each agent gets its own capped key. Sleep soundly.

### More agents

```bash
capit --agents  # List all supported agents
```

See [agents/README.md](capit/agents/README.md) for the full list and adding custom agents.

### First time?

```bash
capit openrouter 5.00 --agent claude -i
```

The `-i` flag prompts for your OpenRouter management key once. It's used to create the capped key.

---

## Platforms

The included platforms are [openrouter](https://openrouter.ai) and [aihubmix](https://aihubmix.com).

Platforms are easy to create with a claude skill located in `skills/platform-creator.md`.

See [platforms/README.md](capit/platforms/README.md) for more details.

---

## Administration

```bash
capit --keys list              # List all keys with spending info
capit --keys list openrouter   # List keys from specific provider
capit --keys delete <name>     # Delete a key (e.g., claude-71ad2519)
capit --keys delete 'capit-*'  # Delete keys matching pattern
capit --platforms              # List available platforms
capit --platforms add          # Add a master key
capit --platforms remove       # Remove a master key
capit --agents                 # List supported agents
```

---

## How It Works

1. You run `capit openrouter 5.00 --agent claude`
2. capit calls OpenRouter's API
3. capit creates a **guardrail** with $5 cap
4. capit creates an **API key** with that guardrail
5. capit writes the key to `~/.claude/.credentials.json`
6. Done

The cap is **enforced by OpenRouter**. The key literally cannot spend more than $5.

---

**MIT License**
