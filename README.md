<p align="center">
<img width="500" height="187" alt="capit_500" src="https://github.com/user-attachments/assets/db22c959-ffee-4540-9108-2928e9c73f70" />
<br/>
<a href=https://pypi.org/project/capit><img src=https://badge.fury.io/py/capit.svg/></a>
<br/><strong>Budget per-agent, per-provider, as little or as much as you want</strong>
</p>

```bash
$ uvx capit openrouter 5.00 --agent openclaw -y
$5.00 openrouter key installed into openclaw
```

That's it. Openclaw now has a capped API key. If it goes rogue, it can only cost you $5.

---

## Install

```bash
uvx install capit
```

## Usage

### Give an agent a budget

```bash
# Claude Code - $5 cap
capit openrouter 5.00 --agent claude -y

# Cursor - $10 cap
capit openrouter 10.00 --agent cursor -y

# Windsurf - $5 cap
capit openrouter 5.00 --agent windsurf -y

# OpenClaw - $5 cap
capit openrouter 5.00 --agent openclaw -y
```

Each agent gets its own capped key. Sleep soundly.

### More agents

```bash
capit --agents  # List all supported agents
```

See [agents/README.md](capit/agents/README.md) for the full list and adding custom agents.

### First time?

```bash
capit openrouter 5.00 --agent claude -i -y
```

The `-i` flag prompts for your OpenRouter management key once. It's used to create the capped key.

---

## Platforms

The included platforms are [openrouter](https://openrouter.ai) and [unkey](https://unkey.com). 

Platforms are easy to create with a claude skill located in `skills/platform-creator.md`. 

See [platforms/README.md](capit/platforms/README.md) for more details.

---

## Administration

```bash
capit --keys list              # Your master keys
capit --keys list openrouter   # Capped keys created on OpenRouter
capit --keys delete openrouter <name>  # Delete a key
capit --keys disable claude-*  # Disable keys matching pattern
capit --platforms              # Available platforms
capit --agents                 # Supported agents
```

---

## How It Works

1. You run `capit openrouter 5.00 --agent claude -y`
2. capit calls OpenRouter's API
3. capit creates a **guardrail** with $5 cap
4. capit creates an **API key** with that guardrail
5. capit writes the key to `~/.claude/.credentials.json`
6. Done

The cap is **enforced by OpenRouter**. The key literally cannot spend more than $5.

---

**MIT License**
