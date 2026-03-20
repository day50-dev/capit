#!/usr/bin/env python3
"""capit - Cap spending on your AI agents.

Usage:
    ./capit.py openrouter 1.00                    # Issue a limited key
    ./capit.py openrouter 1.00 --agent claude    # Send to agent
    ./capit.py --keys list -p openrouter         # List provider keys
    ./capit.py --help                            # Show help
"""

import sys
from pathlib import Path

# Add the capit package to the path
sys.path.insert(0, str(Path(__file__).parent))

from capit import cli

if __name__ == "__main__":
    cli()
