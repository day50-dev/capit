# capit

capit is a command line tool that issues authentication keys based on a master key with a spending cap.

It is intended to be an alternative to more complicated secrets management platforms such as vault, doppler and nordpass for use-cases where you have a credit card hooked up to an account and don't necessarily trust what you're feeding your api keys into.

It's a locally run solution and there's nobody trying to make money behind it. No signup, nothing like that.

## Quick Start

```shell
$ capit openrouter 1.00
sk-or-v1-...
```

## Installation

```bash
# Clone or download this repository
cd limitspend

# Install with pip
pip install -e .

# Or use a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage

### Key Issuance (Primary Workflow)

The main use case - issue a limited key with a spending cap:

```shell
$ capit <platform> <spend_cap>
$ capit openrouter 1.00
sk-or-v1-...
```

### Administration Commands

All administration commands use `--` prefix for clean separation from key issuance.

**List platforms:**
```shell
$ capit --platforms
example
openrouter
```

**List stores:**
```shell
$ capit --stores
dotenv
```

**Manage master keys:**
```shell
# Add a key
$ capit --keys add openrouter
Store: dotenv
Add key:
Key: sk-or-v1-your-actual-key-here
Key added

# List keys
$ capit --keys list
openrouter | dotenv

# Remove a key
$ capit --keys remove openrouter
Success
```

**Enable/disable platforms:**
```shell
$ capit --disable openrouter
Platform 'openrouter' disabled

$ capit --enable openrouter
Platform 'openrouter' enabled
```

## Platforms

### OpenRouter

capit integrates with [OpenRouter](https://openrouter.ai) to create real limited API keys with spending caps.

When you issue a key for OpenRouter, capit:
1. Creates a **guardrail** on OpenRouter with your specified budget limit
2. Creates a new **API key** with that guardrail assigned
3. Returns the limited key

This means the spending cap is **enforced by OpenRouter**, not just locally generated.

**Requirements:**
- A Management API key from [openrouter.ai/settings/management-keys](https://openrouter.ai/settings/management-keys)
- The key must have permissions to create API keys and guardrails

**Example:**
```shell
# Add your OpenRouter management key
$ capit --keys add openrouter
Store: dotenv
Add key:
Key: sk-or-v1-management-key-...
Key added

# Issue a limited key with $5/month cap
$ capit openrouter 5.00
sk-or-v1-limited-key-...
```

The returned key will have a $5/month spending limit enforced by OpenRouter.

### Adding New Platforms

capit is user-modifiable. See [new-platform.md](new-platform.md) for adding new platforms.

Platform code is auditable, locally run code. Template available at `capit/platforms/example.py`.

```shell
$ capit --platforms
example
openrouter
```

## Storage (Stores)

The storage platform for your reference keys (the ones with the ability to create limit keys) is also user-modifiable and modular. This means you can gate things behind say, a yubi-key before they are issued, or you can just be lazy.

```shell
$ capit --stores
dotenv
```

Will list the store methods, the default being a `.env` style format called `secrets.txt` in `$HOME/.local/capit`.

You can find how these are implemented in `capit/stores/` - it's two functions, `store_key` and `retrieve_key`, not too hard. This follows the same pattern as the platforms.

### Adding a New Master Key

It will add a key in the way you specify and then also put an entry into `$HOME/.local/capit/master-lookup` that tells what kind of store the platform is using so:
1. It can be restored in the future
2. You can have different store technologies for different master keys
3. Changing the default store doesn't blow away all your previously added keys

```shell
$ capit --keys add openrouter
Store: dotenv
Add key:
Key: [your-key]
Key added
```

## Directory Structure

```
limitspend/
├── pyproject.toml         # Package configuration
├── README.md              # This file
├── new-platform.md        # Guide for adding new platforms
└── capit/                 # Main package
    ├── __init__.py        # CLI implementation
    ├── platforms/         # Platform implementations
    │   ├── __init__.py
    │   ├── openrouter.py  # OpenRouter with real API integration
    │   └── example.py     # Template for new platforms
    └── stores/            # Storage backend implementations
        ├── __init__.py
        └── dotenv.py      # Default text-file store
```

## Configuration

capit stores configuration in `$HOME/.local/capit/`:
- `secrets.txt` - Master keys (dotenv format)
- `master-lookup` - JSON mapping of platforms to stores

## License

MIT
