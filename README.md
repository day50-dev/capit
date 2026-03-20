<p align="center">
<img width="500" height="187" alt="capit_500" src="https://github.com/user-attachments/assets/db22c959-ffee-4540-9108-2928e9c73f70" />
<br/>
<a href=https://pypi.org/project/capit><img src=https://badge.fury.io/py/capit.svg/></a>
<br/><strong>Buget per-agent, per-provider, as little or as much as you want</strong>
</p>

```bash
$ uvx capit openrouter 5.00 --agent openclaw
$5.00 openrouter key installed into openclaw
```

That's it. You now have an API key with a **$5/month spending cap** enforced by OpenRouter installed into openclaw's setting file. If it goes rogue, it can only spend $5.

## The Problem

You want to use AI agents but you don't trust them with unlimited access to your credit card:

- Claude Code might get stuck in a loop
- Cursor might burn through tokens debugging
- Your custom agent might have a bug
- You want to try multiple agents without risk

Traditional secrets management is overkill. You just want a **spending limit**.

## The Solution

capit creates **limited API keys** with spending caps enforced by the provider:

```bash
# Give Claude Code a $5/month cap
capit openrouter 5.00 --agent claude

# Give Cursor a $10/month cap  
capit openrouter 10.00 --agent cursor

# Give your custom agent a $1/month cap
capit openrouter 1.00
```

## Quick Start

### Install

```bash
pip install capit
```

### Issue a limited key

```bash
# Basic: $1/month cap
capit openrouter 1.00

# Named key for organization
capit openrouter 5.00 --name claude --prefix prod

# Send directly to your agent (auto-configures + auto-names the key)
capit openrouter 5.00 --agent claude

# Skip confirmation prompt
capit openrouter 5.00 --agent claude -y
```

### First time? No setup friction

```bash
$ capit openrouter 5.00 -i
No master key found for 'openrouter'.
Enter your management API key (won't be stored):
Key: sk-or-v1-management-...
sk-or-v1-limited-key-...
```

The `-i` flag prompts for your management key once, uses it to create the limited key, and discards it. Perfect for trying it out.

## Consumers

"Consumers" are AI agents and tools that use API keys. capit sends capped keys directly to them:

```bash
# List available consumers
capit --consumers
# claude
# cursor
# windsurf
# example

# Send to a consumer
capit openrouter 5.00 --agent claude
```

### Built-in consumers

| Consumer | Command |
|----------|---------|
| Claude / Claude Code | `capit openrouter 5.00 --agent claude` |
| Cursor IDE | `capit openrouter 10.00 --agent cursor` |
| Windsurf | `capit openrouter 5.00 --agent windsurf` |

### Example: Claude Code

```bash
# Create a $5/month capped key and get instructions
$ capit openrouter 5.00 --agent claude

🔑 Generated limited key for openrouter ($5.00 cap)
Key: sk-or-v1-...

To use with Claude, run:
  export OPENROUTER_API_KEY=sk-or-v1-...

Or pipe to claude-code:
  OPENROUTER_API_KEY=sk-or-v1-... claude
```

Now Claude can only spend $5/month. Sleep soundly.

### Add your own consumer

Consumers live in `capit/consumers/`. To add one:

```bash
# Copy the template
cp capit/consumers/example.py capit/consumers/myagent.py

# Edit it to customize for your tool
```

The `send()` function in your consumer file gets called with the key and should output instructions or configure your tool. See [new-platform.md](new-platform.md) for details.

## For Agent Authors

If you're building an AI agent, make it a **consumer**:

### Option 1: Document the command

Tell users to run:
```bash
capit openrouter 5.00 --agent your-agent
```

### Option 2: Integrate directly

Add a handler in your setup script:

```python
# In your agent's install/setup script
import subprocess

def setup_api_key():
    result = subprocess.run(
        ["capit", "openrouter", "5.00", "--agent", "your-agent"],
        capture_output=True,
        text=True
    )
    # Parse the key from output and configure
```

### Option 3: Create a custom consumer

Add your handler to capit (or fork and customize):

```python
def send_to_youragent(key, platform, spend_cap):
    click.echo(f"\n🔑 Limited key for {platform} (${spend_cap} cap)")
    click.echo(f"Key: {key}")
    click.echo(f"\nAdd to ~/.youragent/config:")
    click.echo(f"  api_key: {key}")
    # Or write directly to config file
    return key
```

## Administration

All admin commands use `--` prefix (Unix style):

```bash
# List your stored master keys
capit --keys list

# Add a master key (stored locally for future use)
capit --keys add openrouter

# List actual API keys created on OpenRouter
capit --keys list -r openrouter
# Output:
#   4ab1e7e3ebc75228...  prod-claude-abc123    $5    2026-03-19  [active]
#   5f54d6da2cdf0d47...  dev-testing-def456    $1    2026-03-19  [active]

# Revoke a specific API key
capit --keys delete openrouter 4ab1e7e3ebc75228

# Remove a stored master key
capit --keys remove openrouter

# List platforms
capit --platforms

# List storage backends
capit --stores
```

## How It Works

1. You run `capit openrouter 5.00`
2. capit calls OpenRouter's Management API
3. capit creates a **guardrail** with $5/month budget limit
4. capit creates an **API key** with that guardrail attached
5. You get back a limited key: `sk-or-v1-...`

The spending cap is **enforced by OpenRouter**, not just locally tracked. The key literally cannot spend more than the cap.

## Platforms

capit works with multiple platforms:

### OpenRouter (LLM APIs)

Creates keys with spending caps enforced by OpenRouter. Perfect for AI agents.

```bash
capit openrouter 5.00 --agent claude
```

### Unkey (Rate-limited API keys)

Creates keys with rate limits and usage caps. Perfect for API access control.

```bash
# 100 credits/month + 10 requests/minute rate limit
capit unkey 100 --name my-api --prefix prod
```

Unkey supports:
- **Usage limits** - Cap total API calls (credits)
- **Rate limits** - Requests per second/minute/hour
- **Auto-refill** - Daily or monthly credit restoration
- **Key expiration** - Temporary keys that auto-expire

See [new-platform.md](new-platform.md) for adding more platforms.

## Storage

Master keys are stored locally in `$HOME/.local/capit/`:
- `secrets.txt` - Your master keys (dotenv format)
- `master-lookup` - Maps platforms to storage backends

You can implement custom storage backends (YubiKey-gated, encrypted, etc.). See `capit/stores/dotenv.py` for the interface.

## One-shot / Ephemeral Mode

Don't want to store anything? Use `-i` to enter your key once:

```bash
capit openrouter 5.00 -i
```

The key is used to create the limited key, then discarded. Next time you'll be prompted again. Perfect for:
- Trying capit for the first time
- CI/CD environments
- Shared machines

## Why This Matters

AI agents are powerful but unpredictable. You should be able to:

1. **Try new agents** without financial risk
2. **Give different agents different budgets** (Claude gets $10, experimental agent gets $1)
3. **Revoke access instantly** when you're done
4. **Sleep soundly** knowing your credit card is safe

capit makes this trivial. One command. Done.

## License

MIT
