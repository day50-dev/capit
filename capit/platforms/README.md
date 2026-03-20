# capit Platforms

Platforms define how capit creates limited keys for different services.

## Built-in Platforms

### OpenRouter (LLM APIs)

**Best for:** AI agents (Claude Code, Cursor, Windsurf, etc.)

```bash
capit openrouter 5.00 --agent claude -y
```

Creates API keys with USD spending caps enforced by OpenRouter. The key literally cannot spend more than the cap.

**Features:**
- Hard USD spending cap
- Enforced by OpenRouter
- Works with 100+ LLM models
- Auto-created guardrails

### Unkey (API Access Control)

**Best for:** Your own APIs, rate limiting, usage quotas

```bash
capit unkey 100 --name my-api --prefix prod
```

Creates API keys with rate limits and credit quotas.

**Features:**
- Rate limits (requests/second, minute, hour)
- Credit quotas (total API calls)
- Optional auto-refill (daily/monthly)
- Temporary keys (auto-expire)
- Shared limits across multiple keys

## Adding Platforms

### Ask Claude

Use the platform-creator skill in the `skills/` directory:

```
Add a new platform for Anthropic that creates API keys with spending limits
```

See [skills/platform-creator.md](../skills/platform-creator.md) for details.

### Manual

1. Copy the template:
   ```bash
   cp capit/platforms/example.py capit/platforms/anthropic.py
   ```

2. Implement the `create_limited_key()` function

3. Test:
   ```bash
   capit --platforms  # Should list anthropic
   capit anthropic 5.00
   ```

## Platform Interface

```python
"""MyPlatform implementation for capit."""

PLATFORM_NAME = "myplatform"
PLATFORM_URL = "https://myplatform.com"
API_BASE = "https://api.myservice.com/v1"  # Required for online mode


def create_limited_key(
    master_key: str,
    spend_cap: str,
    salt: str,
    name: str = None,
    prefix: str = None
) -> str:
    """Create a limited key with spending/rate limits.
    
    Returns the created API key string.
    """
    # Call platform API to create key with limits
    ...
    return key
```

## Listing Platforms

```bash
capit --platforms
# example
# openrouter
# unkey
# myplatform
```
