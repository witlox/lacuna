"""Version information for Lacuna."""

import os
import subprocess
from datetime import datetime
from pathlib import Path


def _get_version() -> str:
    """Generate version as year.major.buildnumber."""
    # First, try to read from static version file (created during build)
    version_file = Path(__file__).parent / "_version.txt"
    if version_file.exists():
        return version_file.read_text().strip()

    # Otherwise, generate from git (development mode)
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

    version = f"{year}.{major}.{commit_count}"

    # If in build context (LACUNA_BUILD env var set), write static version
    if os.environ.get("LACUNA_BUILD"):
        try:
            version_file.write_text(version)
        except Exception:
            pass  # Don't fail build if we can't write version file

    return version


__version__ = _get_version()
