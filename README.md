# capit

**Cap spending on your API keys. One command.**

```bash
$ capit openrouter 1.00
sk-or-v1-64bfb358fa0a...
```

That's it. You now have an API key with a $1/month spending cap enforced by OpenRouter.

## Quick Start

### Issue a limited key

```bash
# Install
pip install capit

# Issue a key with $1/month cap
capit openrouter 1.00
```

### First time? No setup needed

```bash
$ capit openrouter 5.00 -i
No master key found for 'openrouter'.
Enter your management API key (won't be stored):
Key: sk-or-v1-management-key...
sk-or-v1-limited-key-...
```

The `-i` flag prompts for your management key without storing it. Perfect for trying it out.

### Send directly to your AI agent

```bash
# Claude
capit openrouter 1.00 --send-to claude

# Cursor IDE
capit openrouter 1.00 --send-to cursor

# Windsurf
capit openrouter 1.00 --send-to windsurf
```

## The Problem

You want to use AI agents (Claude Code, Cursor, etc.) but you don't want to give them unlimited access to your credit card. Traditional secrets management is overkill.

## The Solution

capit creates **limited API keys** with spending caps enforced by the provider:

1. You run `capit openrouter 5.00`
2. capit calls OpenRouter's API to create a guardrail with $5/month limit
3. capit creates an API key with that guardrail attached
4. You give the limited key to your agent

If the agent goes rogue, it can only spend $5.

## Consumers

"Consumers" are AI agents and tools that use API keys. capit can send keys directly to them:

| Consumer | Command |
|----------|---------|
| Claude / Claude Code | `capit openrouter 1.00 --send-to claude` |
| Cursor IDE | `capit openrouter 1.00 --send-to cursor` |
| Windsurf | `capit openrouter 1.00 --send-to windsurf` |

### Create your own consumer

Add a handler in your script:

```python
def send_to_mytool(key, platform, spend_cap):
    print(f"export API_KEY={key}")
    # Or write to a config file, or call an API, etc.
```

## Administration

All admin commands use `--` prefix (Unix style):

```bash
# List your stored master keys
capit --keys list

# Add a master key (stored locally)
capit --keys add openrouter

# List actual API keys created on OpenRouter
capit --keys list -r openrouter

# Revoke an API key
capit --keys delete openrouter <key-id>

# Remove a stored master key
capit --keys remove openrouter

# List platforms
capit --platforms

# List storage backends
capit --stores
```

## Platforms

Platforms define how to create limited keys for a service:

```bash
capit --platforms
# example
# openrouter
```

### Adding a platform

See [new-platform.md](new-platform.md) for the full guide. Quick example:

```python
# capit/platforms/anthropic.py
PLATFORM_NAME = "anthropic"
PLATFORM_URL = "https://anthropic.com"
API_BASE = "https://api.anthropic.com/v1"

def create_limited_key(master_key, spend_cap, salt, name=None, prefix=None):
    # Call Anthropic API to create limited key
    ...
```

## Storage

Master keys are stored locally in `$HOME/.local/capit/`:
- `secrets.txt` - Your master keys (dotenv format)
- `master-lookup` - Maps platforms to storage backends

You can implement custom storage backends (e.g., YubiKey-gated, encrypted, etc.). See `capit/stores/dotenv.py` for the interface.

## One-shot / Ephemeral Mode

Don't want to store anything? Use `-i` to enter your key once:

```bash
capit openrouter 1.00 -i
```

The key is used to create the limited key, then discarded. Next time you'll be prompted again.

## For Agent Authors

If you're building an AI agent, integrate capit:

```bash
# In your setup script
LIMITED_KEY=$(capit openrouter 5.00 -s claude)
export OPENROUTER_API_KEY=$LIMITED_KEY
```

Or let users cap spending for your agent:

```bash
# User runs your agent with spending cap
capit openrouter 10.00 --send-to my-agent
```

## License

MIT
