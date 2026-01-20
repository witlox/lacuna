"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from lacuna.config.loader import ConfigLoader


class TestConfigLoaderInit:
    """Tests for ConfigLoader initialization."""

    def test_loader_creates_directory(self) -> None:
        """Test that loader creates config directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "nonexistent" / "config"
            _loader = ConfigLoader(config_dir)

            assert config_dir.exists()

    def test_loader_uses_existing_directory(self) -> None:
        """Test that loader uses existing config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            loader = ConfigLoader(config_dir)

            assert loader.config_dir == config_dir


class TestConfigLoaderLoad:
    """Tests for loading configuration files."""

    def test_load_single_file(self) -> None:
        """Test loading a single configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create a test config file
            config_data = {
                "classification": {
                    "strategy": "hybrid",
                    "heuristic_enabled": True,
                }
            }
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config_data, f)

            loader = ConfigLoader(config_dir)
            loaded = loader.load("test.yaml")

            assert loaded["classification"]["strategy"] == "hybrid"
            assert loaded["classification"]["heuristic_enabled"] is True

    def test_load_nonexistent_file_returns_empty(self) -> None:
        """Test that loading nonexistent file returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))
            loaded = loader.load("nonexistent.yaml")

            assert loaded == {}

    def test_load_empty_file_returns_empty(self) -> None:
        """Test that loading empty file returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_file = config_dir / "empty.yaml"
            config_file.touch()  # Create empty file

            loader = ConfigLoader(config_dir)
            loaded = loader.load("empty.yaml")

            assert loaded == {}


class TestConfigLoaderLoadAll:
    """Tests for loading all configuration files."""

    def test_load_all_merges_files(self) -> None:
        """Test that load_all merges multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create default.yaml
            default = {"database": {"host": "localhost"}, "debug": False}
            with open(config_dir / "default.yaml", "w") as f:
                yaml.safe_dump(default, f)

            # Create classification_patterns.yaml
            patterns = {"patterns": ["SSN", "email"]}
            with open(config_dir / "classification_patterns.yaml", "w") as f:
                yaml.safe_dump(patterns, f)

            loader = ConfigLoader(config_dir)
            config = loader.load_all()

            assert config["database"]["host"] == "localhost"
            assert config["patterns"] == ["SSN", "email"]

    def test_load_all_override_priority(self) -> None:
        """Test that later files override earlier ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create default.yaml with initial value
            default = {"setting": "default", "nested": {"key": "default"}}
            with open(config_dir / "default.yaml", "w") as f:
                yaml.safe_dump(default, f)

            # Create plugins.yaml with override
            plugins = {"setting": "override", "plugin": "value"}
            with open(config_dir / "plugins.yaml", "w") as f:
                yaml.safe_dump(plugins, f)

            loader = ConfigLoader(config_dir)
            config = loader.load_all()

            assert config["setting"] == "override"
            assert config["plugin"] == "value"


class TestConfigLoaderDeepMerge:
    """Tests for deep merge functionality."""

    def test_deep_merge_simple(self) -> None:
        """Test simple deep merge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))

            base = {"a": 1, "b": 2}
            override = {"b": 3, "c": 4}

            result = loader._deep_merge(base, override)

            assert result["a"] == 1
            assert result["b"] == 3
            assert result["c"] == 4

    def test_deep_merge_nested(self) -> None:
        """Test nested deep merge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))

            base = {
                "level1": {
                    "level2a": {"key1": "value1"},
                    "level2b": {"key2": "value2"},
                }
            }
            override = {
                "level1": {
                    "level2a": {"key1": "override1", "key3": "value3"},
                }
            }

            result = loader._deep_merge(base, override)

            assert result["level1"]["level2a"]["key1"] == "override1"
            assert result["level1"]["level2a"]["key3"] == "value3"
            assert result["level1"]["level2b"]["key2"] == "value2"

    def test_deep_merge_replaces_non_dict(self) -> None:
        """Test that non-dict values are replaced entirely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))

            base = {"list": [1, 2, 3], "value": "original"}
            override = {"list": [4, 5], "value": "new"}

            result = loader._deep_merge(base, override)

            assert result["list"] == [4, 5]  # Replaced, not merged
            assert result["value"] == "new"


class TestConfigLoaderSave:
    """Tests for saving configuration files."""

    def test_save_config(self) -> None:
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            loader = ConfigLoader(config_dir)

            config = {
                "setting": "value",
                "nested": {"key": "nested_value"},
            }

            loader.save("saved.yaml", config)

            # Verify file was created
            saved_file = config_dir / "saved.yaml"
            assert saved_file.exists()

            # Verify content
            with open(saved_file) as f:
                loaded = yaml.safe_load(f)

            assert loaded["setting"] == "value"
            assert loaded["nested"]["key"] == "nested_value"

    def test_save_overwrites_existing(self) -> None:
        """Test that save overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            loader = ConfigLoader(config_dir)

            # Save initial config
            loader.save("test.yaml", {"initial": True})

            # Save new config
            loader.save("test.yaml", {"updated": True, "initial": False})

            # Load and verify
            loaded = loader.load("test.yaml")
            assert loaded["updated"] is True
            assert loaded["initial"] is False


class TestConfigLoaderEdgeCases:
    """Tests for edge cases in configuration loading."""

    def test_load_with_complex_types(self) -> None:
        """Test loading config with complex types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            config_data = {
                "list_of_dicts": [
                    {"name": "item1", "value": 1},
                    {"name": "item2", "value": 2},
                ],
                "mixed_list": [1, "two", 3.0, True],
                "nullable": None,
            }
            config_file = config_dir / "complex.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config_data, f)

            loader = ConfigLoader(config_dir)
            loaded = loader.load("complex.yaml")

            assert len(loaded["list_of_dicts"]) == 2
            assert loaded["list_of_dicts"][0]["name"] == "item1"
            assert loaded["mixed_list"] == [1, "two", 3.0, True]
            assert loaded["nullable"] is None

    def test_load_all_missing_files(self) -> None:
        """Test load_all when some files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Only create default.yaml
            default = {"only_default": True}
            with open(config_dir / "default.yaml", "w") as f:
                yaml.safe_dump(default, f)

            loader = ConfigLoader(config_dir)
            config = loader.load_all()

            # Should still work with partial files
            assert config["only_default"] is True
