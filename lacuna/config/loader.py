"""Configuration loader for YAML files."""

from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Load and merge configuration from multiple YAML files."""

    def __init__(self, config_dir: Path):
        """Initialize config loader.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self, filename: str) -> dict[str, Any]:
        """Load a single configuration file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            Configuration dictionary
        """
        config_file = self.config_dir / filename
        if not config_file.exists():
            return {}

        with open(config_file) as f:
            return yaml.safe_load(f) or {}

    def load_all(self) -> dict[str, Any]:
        """Load all configuration files and merge them.

        Returns:
            Merged configuration dictionary
        """
        config: dict[str, Any] = {}

        # Load in priority order
        for filename in [
            "default.yaml",
            "classification_patterns.yaml",
            "proprietary_terms.yaml",
            "plugins.yaml",
        ]:
            file_config = self.load(filename)
            config = self._deep_merge(config, file_config)

        return config

    def _deep_merge(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Dictionary to merge in

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def save(self, filename: str, config: dict[str, Any]) -> None:
        """Save configuration to a YAML file.

        Args:
            filename: Name of the YAML file
            config: Configuration dictionary to save
        """
        config_file = self.config_dir / filename
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
