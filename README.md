<p align="center">
<img width="500" height="187" alt="capit_500" src="https://github.com/user-attachments/assets/db22c959-ffee-4540-9108-2928e9c73f70" />
<br/>
<a href=https://pypi.org/project/capit><img src=https://badge.fury.io/py/capit.svg/></a>
<br/><strong>Budget per-agent, per-provider, as little or as much as you want</strong>
</p>

```bash
$ uvx capit openrouter 5.00 --agent claude -y
$5.00 openrouter key installed into claude
```

That's it. Claude Code now has a capped API key. If it goes rogue, it can only cost you $5.

---

## Install

```bash
pip install capit
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
capit --consumers  # List all supported agents
```

See [consumers/README.md](capit/consumers/README.md) for the full list and adding custom agents.

### First time?

```bash
capit openrouter 5.00 --agent claude -i -y
```

The `-i` flag prompts for your OpenRouter management key once. It's used to create the capped key, then discarded.

---

## Platforms

The included platforms are [openrouter](https://openrouter.ai) and [unkey](https://unkey.com). Platforms are easy to create with a claude skill located in `skills/platform-creator.md`. 
See [platforms/README.md](capit/platforms/README.md) for more details.

---

## Administration

```bash
capit --keys list              # Your master keys
capit --keys list -r openrouter  # Capped keys created on OpenRouter
capit --keys delete openrouter <id>  # Revoke a key
capit --platforms              # Available platforms
capit --consumers              # Supported agents
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
