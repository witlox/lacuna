"""Version information for Lacuna."""

import subprocess
from datetime import datetime


def _get_version() -> str:
    """Generate version as year.major.commitnr."""
    year = datetime.now().year
    major = 1  # Increment manually for breaking changes
    try:
        commit_count = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit_count = "0"
    return f"{year}.{major}.{commit_count}"


__version__ = _get_version()
