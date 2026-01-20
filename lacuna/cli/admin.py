"""Lacuna CLI - Admin commands for configuration management."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
import yaml


def get_config_path() -> Path:
    """Get the configuration directory path."""
    from lacuna.config import get_settings

    return get_settings().config_path


def load_terms_file() -> dict:
    """Load proprietary terms from YAML file."""
    terms_file = get_config_path() / "proprietary_terms.yaml"
    if terms_file.exists():
        with open(terms_file) as f:
            return yaml.safe_load(f) or {}
    return {"projects": [], "customers": [], "terms": []}


def save_terms_file(data: dict) -> None:
    """Save proprietary terms to YAML file."""
    terms_file = get_config_path() / "proprietary_terms.yaml"
    with open(terms_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def load_config_file() -> dict:
    """Load main configuration from YAML file."""
    config_file = get_config_path() / "default.yaml"
    if config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config_file(data: dict) -> None:
    """Save main configuration to YAML file."""
    config_file = get_config_path() / "default.yaml"
    with open(config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


@click.group()
def admin() -> None:
    """Admin commands for managing Lacuna configuration.

    These commands modify configuration files and settings.
    Changes take effect on next restart unless noted otherwise.
    """
    pass


# =============================================================================
# Config Commands
# =============================================================================


@admin.group()
def config() -> None:
    """Manage configuration settings."""
    pass


@config.command("get")
@click.argument("key", required=False)
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def config_get(key: Optional[str], json_output: bool) -> None:
    """Get configuration value(s).

    If KEY is provided, returns that specific value.
    If KEY is omitted, returns all configuration.

    Examples:
        lacuna admin config get
        lacuna admin config get classification.strategy
    """
    config_data = load_config_file()

    if key:
        # Navigate nested keys
        value = config_data
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                click.echo(f"Key not found: {key}", err=True)
                sys.exit(1)

        if json_output:
            click.echo(json.dumps(value, indent=2))
        else:
            click.echo(f"{key} = {value}")
    else:
        if json_output:
            click.echo(json.dumps(config_data, indent=2))
        else:
            click.echo("\n⚙️ Configuration")
            click.echo(f"{'=' * 40}")
            _print_nested_dict(config_data)


def _print_nested_dict(d: dict, prefix: str = "") -> None:
    """Print nested dictionary with indentation."""
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            click.echo(f"{full_key}:")
            _print_nested_dict(value, full_key)
        else:
            click.echo(f"  {full_key} = {value}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value.

    Values are automatically converted to appropriate types.

    Examples:
        lacuna admin config set classification.strategy balanced
        lacuna admin config set classification.confidence_threshold 0.85
        lacuna admin config set audit.enabled true
    """
    config_data = load_config_file()

    # Parse value to appropriate type
    parsed_value = _parse_value(value)

    # Navigate and set nested key
    parts = key.split(".")
    current = config_data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    old_value = current.get(parts[-1], "<not set>")
    current[parts[-1]] = parsed_value

    save_config_file(config_data)
    click.echo(f"✓ Set {key}: {old_value} → {parsed_value}")


def _parse_value(value: str):
    """Parse string value to appropriate type."""
    # Boolean
    if value.lower() in ("true", "yes", "on", "1"):
        return True
    if value.lower() in ("false", "no", "off", "0"):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # String
    return value


@config.command("list")
def config_list() -> None:
    """List all configurable settings with their current values."""
    from lacuna.config import get_settings

    settings = get_settings()

    click.echo("\n⚙️ All Settings")
    click.echo(f"{'=' * 60}")

    sections: list[tuple[str, list[tuple[str, object]]]] = [
        (
            "General",
            [
                ("environment", settings.environment),
                ("debug", settings.debug),
                ("log_level", settings.log_level),
            ],
        ),
        (
            "Classification",
            [
                ("classification.strategy", settings.classification.strategy),
                (
                    "classification.confidence_threshold",
                    settings.classification.confidence_threshold,
                ),
                (
                    "classification.heuristic_enabled",
                    settings.classification.heuristic_enabled,
                ),
                (
                    "classification.embedding_enabled",
                    settings.classification.embedding_enabled,
                ),
                ("classification.llm_enabled", settings.classification.llm_enabled),
            ],
        ),
        (
            "Policy",
            [
                ("policy.enabled", settings.policy.enabled),
                ("policy.opa_endpoint", settings.policy.opa_endpoint),
            ],
        ),
        (
            "Audit",
            [
                ("audit.enabled", settings.audit.enabled),
                ("audit.retention_days", settings.audit.retention_days),
                ("audit.verify_integrity", settings.audit.verify_integrity),
            ],
        ),
        (
            "Lineage",
            [
                ("lineage.enabled", settings.lineage.enabled),
                ("lineage.max_depth", settings.lineage.max_depth),
            ],
        ),
    ]

    for section_name, items in sections:
        click.echo(f"\n{section_name}:")
        for key, value in items:
            click.echo(f"  {key}: {value}")


# =============================================================================
# Terms Commands
# =============================================================================


@admin.group()
def terms() -> None:
    """Manage proprietary terms list."""
    pass


@terms.command("list")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def terms_list(json_output: bool) -> None:
    """List all proprietary terms."""
    data = load_terms_file()
    terms_list = data.get("terms", [])

    if json_output:
        click.echo(json.dumps(terms_list, indent=2))
    else:
        click.echo(f"\n📝 Proprietary Terms ({len(terms_list)})")
        click.echo(f"{'=' * 40}")
        for term in sorted(terms_list):
            click.echo(f"  • {term}")


@terms.command("add")
@click.argument("term")
def terms_add(term: str) -> None:
    """Add a proprietary term.

    Example:
        lacuna admin terms add "Project Alpha"
    """
    data = load_terms_file()
    if "terms" not in data:
        data["terms"] = []

    if term in data["terms"]:
        click.echo(f"Term already exists: {term}", err=True)
        sys.exit(1)

    data["terms"].append(term)
    save_terms_file(data)
    click.echo(f"✓ Added term: {term}")


@terms.command("remove")
@click.argument("term")
def terms_remove(term: str) -> None:
    """Remove a proprietary term.

    Example:
        lacuna admin terms remove "Project Alpha"
    """
    data = load_terms_file()
    if term not in data.get("terms", []):
        click.echo(f"Term not found: {term}", err=True)
        sys.exit(1)

    data["terms"].remove(term)
    save_terms_file(data)
    click.echo(f"✓ Removed term: {term}")


# =============================================================================
# Projects Commands
# =============================================================================


@admin.group()
def projects() -> None:
    """Manage proprietary projects list."""
    pass


@projects.command("list")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def projects_list(json_output: bool) -> None:
    """List all proprietary projects."""
    data = load_terms_file()
    projects = data.get("projects", [])

    if json_output:
        click.echo(json.dumps(projects, indent=2))
    else:
        click.echo(f"\n📁 Proprietary Projects ({len(projects)})")
        click.echo(f"{'=' * 40}")
        for project in sorted(projects):
            click.echo(f"  • {project}")


@projects.command("add")
@click.argument("project")
def projects_add(project: str) -> None:
    """Add a proprietary project.

    Example:
        lacuna admin projects add "internal-ml-model"
    """
    data = load_terms_file()
    if "projects" not in data:
        data["projects"] = []

    if project in data["projects"]:
        click.echo(f"Project already exists: {project}", err=True)
        sys.exit(1)

    data["projects"].append(project)
    save_terms_file(data)
    click.echo(f"✓ Added project: {project}")


@projects.command("remove")
@click.argument("project")
def projects_remove(project: str) -> None:
    """Remove a proprietary project.

    Example:
        lacuna admin projects remove "internal-ml-model"
    """
    data = load_terms_file()
    if project not in data.get("projects", []):
        click.echo(f"Project not found: {project}", err=True)
        sys.exit(1)

    data["projects"].remove(project)
    save_terms_file(data)
    click.echo(f"✓ Removed project: {project}")


# =============================================================================
# Customers Commands
# =============================================================================


@admin.group()
def customers() -> None:
    """Manage proprietary customers list."""
    pass


@customers.command("list")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def customers_list(json_output: bool) -> None:
    """List all proprietary customers."""
    data = load_terms_file()
    customers = data.get("customers", [])

    if json_output:
        click.echo(json.dumps(customers, indent=2))
    else:
        click.echo(f"\n👥 Proprietary Customers ({len(customers)})")
        click.echo(f"{'=' * 40}")
        for customer in sorted(customers):
            click.echo(f"  • {customer}")


@customers.command("add")
@click.argument("customer")
def customers_add(customer: str) -> None:
    """Add a proprietary customer.

    Example:
        lacuna admin customers add "Acme Corp"
    """
    data = load_terms_file()
    if "customers" not in data:
        data["customers"] = []

    if customer in data["customers"]:
        click.echo(f"Customer already exists: {customer}", err=True)
        sys.exit(1)

    data["customers"].append(customer)
    save_terms_file(data)
    click.echo(f"✓ Added customer: {customer}")


@customers.command("remove")
@click.argument("customer")
def customers_remove(customer: str) -> None:
    """Remove a proprietary customer.

    Example:
        lacuna admin customers remove "Acme Corp"
    """
    data = load_terms_file()
    if customer not in data.get("customers", []):
        click.echo(f"Customer not found: {customer}", err=True)
        sys.exit(1)

    data["customers"].remove(customer)
    save_terms_file(data)
    click.echo(f"✓ Removed customer: {customer}")


# =============================================================================
# Policy Commands
# =============================================================================


@admin.group()
def policy() -> None:
    """Manage policy engine settings."""
    pass


@policy.command("status")
def policy_status() -> None:
    """Show policy engine status."""
    from lacuna.config import get_settings

    settings = get_settings()

    click.echo("\n🔒 Policy Engine Status")
    click.echo(f"{'=' * 40}")
    status = "enabled" if settings.policy.enabled else "disabled"
    status_color = "green" if settings.policy.enabled else "yellow"
    click.echo(f"Status: {click.style(status, fg=status_color, bold=True)}")
    click.echo(f"OPA Endpoint: {settings.policy.opa_endpoint or 'Not configured'}")
    click.echo(f"Policy Path: {settings.policy.opa_policy_path}")
    click.echo(f"Timeout: {settings.policy.opa_timeout}s")


@policy.command("enable")
def policy_enable() -> None:
    """Enable the policy engine."""
    config_data = load_config_file()
    if "policy" not in config_data:
        config_data["policy"] = {}
    config_data["policy"]["enabled"] = True
    save_config_file(config_data)
    click.echo("✓ Policy engine enabled (restart required)")


@policy.command("disable")
def policy_disable() -> None:
    """Disable the policy engine."""
    config_data = load_config_file()
    if "policy" not in config_data:
        config_data["policy"] = {}
    config_data["policy"]["enabled"] = False
    save_config_file(config_data)
    click.echo("✓ Policy engine disabled (restart required)")


# =============================================================================
# Users Commands
# =============================================================================


@admin.group()
def users() -> None:
    """Manage and view user information."""
    pass


@users.command("list")
@click.option("--limit", "-l", default=50, help="Maximum users to show")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def users_list(limit: int, json_output: bool) -> None:
    """List users from audit logs.

    Shows users who have interacted with the system.
    """
    from lacuna.audit.logger import AuditLogger
    from lacuna.models.audit import AuditQuery

    logger = AuditLogger()

    try:
        # Query recent audit records to extract unique users
        query = AuditQuery(limit=1000)
        records = logger._backend.query(query)

        # Extract unique users with their last activity
        users_data: dict = {}
        for record in records:
            if record.user_id not in users_data:
                users_data[record.user_id] = {
                    "user_id": record.user_id,
                    "last_activity": record.timestamp.isoformat(),
                    "event_count": 0,
                }
            users_data[record.user_id]["event_count"] += 1

        users_list = sorted(
            users_data.values(),
            key=lambda x: x["event_count"],
            reverse=True,
        )[:limit]

        if json_output:
            click.echo(json.dumps(users_list, indent=2))
        else:
            click.echo(f"\n👥 Users ({len(users_list)})")
            click.echo(f"{'=' * 60}")
            click.echo(f"{'User ID':<30} {'Events':>10} {'Last Activity':<20}")
            click.echo(f"{'-' * 60}")
            for user in users_list:
                click.echo(
                    f"{user['user_id'][:30]:<30} "
                    f"{user['event_count']:>10} "
                    f"{user['last_activity'][:19]:<20}"
                )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        logger.stop()


@users.command("activity")
@click.argument("user_id")
@click.option("--limit", "-l", default=20, help="Maximum records")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def users_activity(user_id: str, limit: int, json_output: bool) -> None:
    """Show activity for a specific user.

    Example:
        lacuna admin users activity analyst@example.com
    """
    from lacuna.audit.logger import AuditLogger
    from lacuna.models.audit import AuditQuery

    logger = AuditLogger()

    try:
        query = AuditQuery(user_id=user_id, limit=limit)
        records = logger._backend.query(query)

        if json_output:
            click.echo(json.dumps([r.to_dict() for r in records], indent=2))
        else:
            click.echo(f"\n📋 Activity for: {user_id}")
            click.echo(f"{'=' * 70}")

            for record in records:
                timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                result_icon = "✓" if record.action_result == "success" else "✗"
                result_color = "green" if record.action_result == "success" else "red"

                click.echo(
                    f"{timestamp} | "
                    f"{record.event_type.value:20} | "
                    f"{click.style(result_icon, fg=result_color)} "
                    f"{record.action_result}"
                )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        logger.stop()
