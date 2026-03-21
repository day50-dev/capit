"""Tests for capit CLI commands."""

import subprocess
import sys
import os
from pathlib import Path

import pytest


@pytest.fixture
def capit_cmd():
    """Get the capit command path."""
    return [sys.executable, str(Path(__file__).parent.parent / "capit.py")]


class TestHelpCommands:
    """Test help output for various commands."""

    def test_main_help(self, capit_cmd):
        """--help should show main usage."""
        result = subprocess.run(
            capit_cmd + ["--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "capit - Cap spending on your AI agents" in result.stdout
        assert "--agent" in result.stdout
        assert "--keys" in result.stdout

    def test_agents_list(self, capit_cmd):
        """--agents should list available agents."""
        result = subprocess.run(
            capit_cmd + ["--agents"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        # Should list at least some agents
        agents_output = result.stdout.strip().split('\n')
        assert len(agents_output) > 0
        # Check for expected agents
        agent_names = [line.strip() for line in agents_output]
        assert "claude" in agent_names
        assert "cursor" in agent_names
        assert "windsurf" in agent_names

    def test_stores_list(self, capit_cmd):
        """--stores should list available stores."""
        result = subprocess.run(
            capit_cmd + ["--stores"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "dotenv" in result.stdout

    def test_platforms_list(self, capit_cmd):
        """--platforms should list available platforms."""
        result = subprocess.run(
            capit_cmd + ["--platforms"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "list" in result.stdout.lower()


class TestKeysCommands:
    """Test --keys subcommands."""

    def test_keys_help(self, capit_cmd):
        """--keys --help should show keys usage."""
        result = subprocess.run(
            capit_cmd + ["--keys", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "list" in result.stdout.lower()
        assert "delete" in result.stdout.lower()

    def test_keys_list_empty(self, capit_cmd, tmp_path, monkeypatch):
        """--keys list should work with no keys."""
        # Use a temp directory for capit config
        capit_dir = tmp_path / ".capit"
        capit_dir.mkdir()
        monkeypatch.setenv("HOME", str(tmp_path))

        result = subprocess.run(
            capit_cmd + ["--keys", "list"],
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(tmp_path)}
        )
        # Should not crash, may show "No keys registered" or empty table
        assert result.returncode == 0 or "No keys" in result.stdout


class TestErrorHandling:
    """Test error handling and logging."""
    # Note: Interactive prompting tests are skipped as they're hard to test reliably
    # The behavior is: prompt for key if not stored, then nag to store it


class TestAgentFlag:
    """Test --agent flag functionality."""

    def test_agent_claude_recognized(self, capit_cmd, monkeypatch, tmp_path):
        """--agent claude should be recognized (may fail auth but not unknown agent)."""
        monkeypatch.setenv("HOME", str(tmp_path))

        # Set up fake platform key to avoid interactive prompt
        capit_dir = tmp_path / ".local" / "capit"
        capit_dir.mkdir(parents=True)
        lookup_file = capit_dir / "master-lookup"
        import json
        lookup_file.write_text(json.dumps({
            "openrouter": {"store": "dotenv", "added_at": "2024-01-01"}
        }))
        secrets_file = capit_dir / "secrets.txt"
        secrets_file.write_text("openrouter=fake_key_for_testing")

        result = subprocess.run(
            capit_cmd + ["openrouter", "5.00", "--agent", "claude"],
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(tmp_path)}
        )

        # Should not fail with "unknown agent" error
        # Will fail with API error (fake key), but that's expected
        assert "Unknown agent" not in result.stderr

    def test_agent_unknown_error(self, capit_cmd, monkeypatch, tmp_path):
        """--agent with unknown agent should error."""
        monkeypatch.setenv("HOME", str(tmp_path))

        # First add a fake platform key so we get past the platform check
        capit_dir = tmp_path / ".local" / "capit"
        capit_dir.mkdir(parents=True)
        lookup_file = capit_dir / "master-lookup"
        import json
        lookup_file.write_text(json.dumps({
            "openrouter": {"store": "dotenv", "added_at": "2024-01-01"}
        }))
        
        # Also need to create a fake dotenv store file
        secrets_file = capit_dir / "secrets.txt"
        secrets_file.write_text("openrouter=fake_key_for_testing")

        result = subprocess.run(
            capit_cmd + ["openrouter", "5.00", "--agent", "nonexistent_agent"],
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(tmp_path)}
        )

        assert result.returncode != 0
        assert "Unknown agent" in result.stderr or "nonexistent" in result.stderr


class TestRemoveAlias:
    """Test that 'remove' works as alias for 'delete'."""

    def test_keys_remove_recognized(self, capit_cmd, monkeypatch, tmp_path):
        """--keys remove should be recognized (same as delete)."""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = subprocess.run(
            capit_cmd + ["--keys", "remove", "nonexistent-pattern"],
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(tmp_path)}
        )

        # Should not fail with "unknown command"
        assert "Unknown command" not in result.stderr
        # Will say "No keys matching" which is fine
        assert result.returncode == 0 or "No keys matching" in result.stdout
