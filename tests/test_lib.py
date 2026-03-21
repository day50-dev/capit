"""Tests for capit.agents.lib module."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from capit.agents.lib import (
    create_backup,
    create_backups,
    show_json_diff,
    install_key,
    _set_nested_value,
    _get_nested_value,
    _display_diff,
)


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_backup_created(self, tmp_path):
        """Backup file should be created with correct naming."""
        # Create original file
        original = tmp_path / "config.json"
        original.write_text('{"key": "value"}')

        # Create backup
        backup = create_backup(original, "testagent")

        # Verify backup exists
        assert backup.exists()
        assert backup.name == "config.json"
        assert "capit-testagent-" in str(backup.parent)

        # Verify content matches
        assert backup.read_text() == original.read_text()

    def test_backup_nonexistent_file(self, tmp_path):
        """Should return None for nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.json"
        result = create_backup(nonexistent, "testagent")
        assert result is None

    def test_backup_naming_pattern(self, tmp_path):
        """Backup directory should follow capit-{agent}-<rand> pattern."""
        original = tmp_path / "config.json"
        original.write_text("{}")

        backup = create_backup(original, "claude")

        assert "capit-claude-" in str(backup.parent)


class TestCreateBackups:
    """Tests for create_backups function."""

    def test_multiple_backups_created(self, tmp_path):
        """Should create backups for multiple files."""
        # Create original files
        file1 = tmp_path / "secrets.json"
        file1.write_text('{"secret": "value1"}')
        file2 = tmp_path / "config.json"
        file2.write_text('{"config": "value2"}')

        files = [(file1, "secrets.json"), (file2, "config.json")]
        backups = create_backups(files, "openclaw")

        # Verify both backups exist
        assert len(backups) == 2
        assert file1 in backups
        assert file2 in backups
        assert backups[file1].exists()
        assert backups[file2].exists()

        # Verify naming pattern
        assert "capit-openclaw-" in str(backups[file1].parent)

    def test_partial_backups(self, tmp_path):
        """Should only backup files that exist."""
        file1 = tmp_path / "exists.json"
        file1.write_text("{}")
        file2 = tmp_path / "missing.json"

        files = [(file1, "exists.json"), (file2, "missing.json")]
        backups = create_backups(files, "testagent")

        # Only existing file should be backed up
        assert len(backups) == 1
        assert file1 in backups


class TestSetNestedValue:
    """Tests for _set_nested_value helper."""

    def test_simple_path(self):
        """Should set value at simple path."""
        data = {}
        _set_nested_value(data, "api_key", "test_value")
        assert data == {"api_key": "test_value"}

    def test_nested_path(self):
        """Should set value at nested path."""
        data = {}
        _set_nested_value(data, "openrouter.key", "test_value")
        assert data == {"openrouter": {"key": "test_value"}}

    def test_deeply_nested_path(self):
        """Should handle deeply nested paths."""
        data = {}
        _set_nested_value(data, "a.b.c.d", "value")
        assert data == {"a": {"b": {"c": {"d": "value"}}}}

    def test_preserve_existing_structure(self):
        """Should preserve existing nested structure."""
        data = {"openrouter": {"other": "value"}}
        _set_nested_value(data, "openrouter.key", "test_value")
        assert data == {"openrouter": {"other": "value", "key": "test_value"}}


class TestGetNestedValue:
    """Tests for _get_nested_value helper."""

    def test_simple_path(self):
        """Should get value at simple path."""
        data = {"api_key": "test_value"}
        result = _get_nested_value(data, "api_key")
        assert result == "test_value"

    def test_nested_path(self):
        """Should get value at nested path."""
        data = {"openrouter": {"key": "test_value"}}
        result = _get_nested_value(data, "openrouter.key")
        assert result == "test_value"

    def test_missing_key(self):
        """Should return default for missing key."""
        data = {"other": "value"}
        result = _get_nested_value(data, "api_key", default=None)
        assert result is None

    def test_missing_nested_key(self):
        """Should return default for missing nested key."""
        data = {"openrouter": {"other": "value"}}
        result = _get_nested_value(data, "openrouter.key", default="default")
        assert result == "default"


class TestInstallKey:
    """Tests for install_key function."""

    def test_install_simple_key(self, tmp_path):
        """Should install key at simple path."""
        config_path = tmp_path / "config.json"

        result = install_key(
            config_path=config_path,
            key_path="api_key",
            key_value="sk-test-key",
            platform="openrouter",
            agent="testagent",
            spend_cap="5.00"
        )

        # Verify return value
        assert result == "sk-test-key"

        # Verify file created with correct content
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config == {"api_key": "sk-test-key"}

        # Verify permissions (0o600)
        mode = os.stat(config_path).st_mode & 0o777
        assert mode == 0o600

    def test_install_nested_key(self, tmp_path):
        """Should install key at nested path."""
        config_path = tmp_path / "config.json"

        install_key(
            config_path=config_path,
            key_path="openrouter.key",
            key_value="sk-test-key",
            platform="openrouter",
            agent="testagent",
            spend_cap="5.00"
        )

        config = json.loads(config_path.read_text())
        assert config == {"openrouter": {"key": "sk-test-key"}}

    def test_install_preserves_existing(self, tmp_path):
        """Should preserve existing config values."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"existing": "value", "other": {"key": "val"}}')

        install_key(
            config_path=config_path,
            key_path="api_key",
            key_value="sk-new-key",
            platform="openrouter",
            agent="testagent",
            spend_cap="5.00"
        )

        config = json.loads(config_path.read_text())
        assert config["existing"] == "value"
        assert config["other"]["key"] == "val"
        assert config["api_key"] == "sk-new-key"

    def test_install_creates_backup(self, tmp_path, capsys):
        """Should create backup when updating existing file."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"api_key": "old-key"}')

        install_key(
            config_path=config_path,
            key_path="api_key",
            key_value="sk-new-key",
            platform="openrouter",
            agent="testagent",
            spend_cap="5.00"
        )

        # Check output mentions backup
        captured = capsys.readouterr()
        assert "backed up to" in captured.out
        assert "capit-testagent-" in captured.out

    def test_install_no_backup_for_new_file(self, tmp_path, capsys):
        """Should not create backup for new file."""
        config_path = tmp_path / "new_config.json"

        install_key(
            config_path=config_path,
            key_path="api_key",
            key_value="sk-new-key",
            platform="openrouter",
            agent="testagent",
            spend_cap="5.00"
        )

        # Check output does not mention backup
        captured = capsys.readouterr()
        assert "backed up" not in captured.out

    def test_install_output_message(self, tmp_path, capsys):
        """Should print correct installation message."""
        config_path = tmp_path / "config.json"

        install_key(
            config_path=config_path,
            key_path="api_key",
            key_value="sk-test-key",
            platform="openrouter",
            agent="claude",
            spend_cap="5.00"
        )

        captured = capsys.readouterr()
        assert "$5.00 openrouter key installed into claude" in captured.out


class TestShowJsonDiff:
    """Tests for show_json_diff function."""

    def test_diff_with_existing_config(self, tmp_path, monkeypatch):
        """Should show diff for existing config."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"api_key": "old-key"}')

        # Mock click.confirm to return True
        monkeypatch.setattr("click.confirm", lambda *args, **kwargs: True)

        result = show_json_diff(
            config_path=config_path,
            key_path="api_key",
            new_value="<new key>",
            agent="testagent",
            platform="openrouter",
            spend_cap="5.00"
        )

        assert result is True

    def test_diff_with_new_config(self, tmp_path, monkeypatch):
        """Should show new config content when no existing file."""
        config_path = tmp_path / "new_config.json"

        # Mock click.confirm
        monkeypatch.setattr("click.confirm", lambda *args, **kwargs: True)

        result = show_json_diff(
            config_path=config_path,
            key_path="api_key",
            new_value="<new key>",
            agent="testagent",
            platform="openrouter",
            spend_cap="5.00"
        )

        assert result is True

    def test_diff_user_declines(self, tmp_path, monkeypatch):
        """Should return False when user declines."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"api_key": "old-key"}')

        # Mock click.confirm to return False
        monkeypatch.setattr("click.confirm", lambda *args, **kwargs: False)

        result = show_json_diff(
            config_path=config_path,
            key_path="api_key",
            new_value="<new key>",
            agent="testagent",
            platform="openrouter",
            spend_cap="5.00"
        )

        assert result is False

    def test_diff_nested_path(self, tmp_path, monkeypatch):
        """Should handle nested key paths."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"openrouter": {"key": "old-key"}}')

        monkeypatch.setattr("click.confirm", lambda *args, **kwargs: True)

        result = show_json_diff(
            config_path=config_path,
            key_path="openrouter.key",
            new_value="<new key>",
            agent="testagent",
            platform="openrouter",
            spend_cap="5.00"
        )

        assert result is True


class TestDisplayDiff:
    """Tests for _display_diff function."""

    def test_display_diff_basic(self, tmp_path, capsys):
        """Should display diff between two files."""
        file1 = tmp_path / "old.json"
        file1.write_text('{"key": "old"}')
        file2 = tmp_path / "new.json"
        file2.write_text('{"key": "new"}')

        _display_diff(str(file1), str(file2))

        captured = capsys.readouterr()
        # Diff output should contain the changes
        assert "old" in captured.out or "new" in captured.out


class TestSimpleAgentSend:
    """Tests for simple_agent_send function."""

    def test_simple_send(self, tmp_path, capsys):
        """Should install key using simple_agent_send."""
        config_path = tmp_path / "config.json"

        from capit.agents.lib import simple_agent_send

        result = simple_agent_send(
            key="sk-test-key",
            platform="openrouter",
            spend_cap="5.00",
            agent="testagent",
            config_path=config_path,
            key_path="api_key"
        )

        assert result == "sk-test-key"
        config = json.loads(config_path.read_text())
        assert config == {"api_key": "sk-test-key"}
