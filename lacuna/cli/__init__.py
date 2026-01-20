"""Lacuna CLI - Command-line interface for data governance."""

import json
import sys
from datetime import datetime
from typing import Optional

import click
import structlog

from lacuna.__version__ import __version__
from lacuna.cli.admin import admin as admin_commands

# Configure structlog for CLI
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


@click.group()
@click.version_option(version=__version__, prog_name="lacuna")
@click.option("--debug/--no-debug", default=False, help="Enable debug output")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Lacuna - Privacy-aware data governance and lineage tracking.

    The protected space where your knowledge stays yours.
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    if debug:
        import logging

        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.argument("query")
@click.option("--project", "-p", help="Project context")
@click.option("--user", "-u", default="cli-user", help="User ID")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
@click.pass_context
def classify(
    ctx: click.Context,
    query: str,
    project: Optional[str],
    user: str,
    json_output: bool,
) -> None:
    """Classify a query or text for data sensitivity.

    Example:
        lacuna classify "How do we handle customer data?"
    """
    from lacuna.engine.governance import GovernanceEngine
    from lacuna.models.classification import ClassificationContext

    engine = GovernanceEngine()
    context = ClassificationContext(user_id=user, project=project)

    try:
        classification = engine.classify(query, context)

        if json_output:
            click.echo(json.dumps(classification.to_dict(), indent=2))
        else:
            click.echo("\n🔍 Classification Result")
            click.echo(f"{'=' * 40}")
            click.echo(f"Tier: {click.style(classification.tier.value, bold=True)}")
            click.echo(f"Confidence: {classification.confidence:.0%}")
            click.echo(f"Reasoning: {classification.reasoning}")
            if classification.tags:
                click.echo(f"Tags: {', '.join(classification.tags)}")
            click.echo(f"Classifier: {classification.classifier_name}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        engine.stop()


@cli.command()
@click.argument("source")
@click.argument("destination")
@click.option("--user", "-u", default="cli-user", help="User ID")
@click.option("--purpose", "-P", help="Business justification")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
@click.pass_context
def evaluate(
    ctx: click.Context,
    source: str,
    destination: str,
    user: str,
    purpose: Optional[str],
    json_output: bool,
) -> None:
    """Evaluate a data export operation against policies.

    Example:
        lacuna evaluate customers.csv ~/Downloads/export.csv
    """
    from lacuna.engine.governance import GovernanceEngine

    engine = GovernanceEngine()

    try:
        result = engine.evaluate_export(
            source=source,
            destination=destination,
            user_id=user,
            purpose=purpose,
        )

        if json_output:
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            if result.allowed:
                click.echo(click.style("\n✓ Operation Allowed", fg="green", bold=True))
            else:
                click.echo(click.style("\n❌ Operation Denied", fg="red", bold=True))

            click.echo(f"{'=' * 40}")
            click.echo(f"Classification: {result.tier or 'Unknown'}")
            click.echo(f"Reasoning: {result.reasoning}")

            if result.tags:
                click.echo(f"Tags: {', '.join(result.tags)}")

            if result.alternatives:
                click.echo("\nAlternatives:")
                for i, alt in enumerate(result.alternatives, 1):
                    click.echo(f"  {i}. {alt}")

            if result.matched_rules:
                click.echo(f"\nMatched Rules: {', '.join(result.matched_rules)}")

            if result.total_latency_ms:
                click.echo(f"\nLatency: {result.total_latency_ms:.2f}ms")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        engine.stop()


@cli.group()
def audit() -> None:
    """Audit log commands."""
    pass


@audit.command("verify")
@click.option("--start", "-s", help="Start time (ISO format)")
@click.option("--end", "-e", help="End time (ISO format)")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def audit_verify(
    start: Optional[str],
    end: Optional[str],
    json_output: bool,
) -> None:
    """Verify audit log integrity using hash chain.

    Example:
        lacuna audit verify --start 2025-01-01
    """
    from lacuna.audit.logger import AuditLogger

    logger = AuditLogger()

    try:
        start_time = datetime.fromisoformat(start) if start else None
        end_time = datetime.fromisoformat(end) if end else None

        result = logger.verify_integrity(start_time, end_time)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            if result["verified"]:
                click.echo(
                    click.style(
                        "\n✓ Audit Log Integrity Verified", fg="green", bold=True
                    )
                )
            else:
                click.echo(
                    click.style("\n❌ Audit Log Integrity Failed", fg="red", bold=True)
                )

            click.echo(f"{'=' * 40}")
            click.echo(f"Records Checked: {result['records_checked']}")
            click.echo(f"Message: {result['message']}")

            if result.get("first_record"):
                click.echo(f"First Record: {result['first_record']}")
            if result.get("last_record"):
                click.echo(f"Last Record: {result['last_record']}")

            if result.get("errors"):
                click.echo(f"\nErrors ({len(result['errors'])}):")
                for error in result["errors"][:5]:  # Show first 5 errors
                    click.echo(f"  - {error['event_id']}: {error['error']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        logger.stop()


@audit.command("query")
@click.option("--user", "-u", help="Filter by user ID")
@click.option("--resource", "-r", help="Filter by resource ID")
@click.option("--start", "-s", help="Start time (ISO format)")
@click.option("--limit", "-l", default=20, help="Maximum records")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def audit_query(
    user: Optional[str],
    resource: Optional[str],
    start: Optional[str],
    limit: int,
    json_output: bool,
) -> None:
    """Query audit log records.

    Example:
        lacuna audit query --user analyst@example.com --limit 10
    """
    from lacuna.audit.logger import AuditLogger
    from lacuna.models.audit import AuditQuery

    logger = AuditLogger()

    try:
        query = AuditQuery(
            user_id=user,
            resource_id=resource,
            start_time=datetime.fromisoformat(start) if start else None,
            limit=limit,
        )

        records = logger._backend.query(query)

        if json_output:
            click.echo(json.dumps([r.to_dict() for r in records], indent=2))
        else:
            click.echo(f"\n📋 Audit Records ({len(records)})")
            click.echo(f"{'=' * 60}")

            for record in records:
                timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                result_color = "green" if record.action_result == "success" else "red"
                result_icon = "✓" if record.action_result == "success" else "✗"

                click.echo(
                    f"{timestamp} | "
                    f"{record.user_id[:20]:20} | "
                    f"{record.event_type.value:20} | "
                    f"{click.style(result_icon, fg=result_color)} "
                    f"{record.action_result}"
                )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        logger.stop()


@cli.group()
def lineage() -> None:
    """Lineage tracking commands."""
    pass


@lineage.command("show")
@click.argument("artifact_id")
@click.option("--depth", "-d", default=10, help="Maximum depth")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def lineage_show(artifact_id: str, depth: int, json_output: bool) -> None:
    """Show lineage for an artifact.

    Example:
        lacuna lineage show analysis.csv
    """
    from lacuna.lineage.tracker import LineageTracker

    tracker = LineageTracker()

    try:
        graph = tracker.get_lineage(artifact_id)

        if json_output:
            click.echo(json.dumps(graph.to_dict(), indent=2))
        else:
            click.echo(f"\n🔗 Lineage Graph for: {artifact_id}")
            click.echo(f"{'=' * 40}")
            click.echo(tracker.to_graph(artifact_id))

            upstream = tracker.get_upstream(artifact_id)
            downstream = tracker.get_downstream(artifact_id)

            click.echo(f"\nUpstream: {len(upstream)} artifacts")
            click.echo(f"Downstream: {len(downstream)} artifacts")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@lineage.command("impact")
@click.argument("artifact_id")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def lineage_impact(artifact_id: str, json_output: bool) -> None:
    """Analyze impact of changes to an artifact.

    Example:
        lacuna lineage impact customers.csv
    """
    from lacuna.lineage.tracker import LineageTracker

    tracker = LineageTracker()

    try:
        analysis = tracker.get_impact_analysis(artifact_id)

        if json_output:
            # Convert int keys to strings for JSON
            analysis["by_depth"] = {
                str(k): v for k, v in analysis.get("by_depth", {}).items()
            }
            click.echo(json.dumps(analysis, indent=2))
        else:
            click.echo(f"\n⚡ Impact Analysis for: {artifact_id}")
            click.echo(f"{'=' * 40}")
            click.echo(f"Downstream Artifacts: {analysis['downstream_count']}")

            if analysis["downstream_artifacts"]:
                click.echo("\nAffected Artifacts:")
                for artifact in analysis["downstream_artifacts"][:10]:
                    click.echo(f"  - {artifact}")

                if analysis["downstream_count"] > 10:
                    click.echo(f"  ... and {analysis['downstream_count'] - 10} more")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option("--reload/--no-reload", default=True, help="Enable auto-reload")
def dev(host: str, port: int, reload: bool) -> None:
    """Start Lacuna in development mode with lightweight backends.

    Uses SQLite database, in-memory caching, and disables heavy services
    like embedding models and LLM classification.

    Example:
        lacuna dev
        lacuna dev --port 8080
    """
    import os
    import shutil
    from pathlib import Path

    import uvicorn

    # Set environment to development
    os.environ["LACUNA_ENVIRONMENT"] = "development"
    os.environ["LACUNA_DEBUG"] = "true"

    # Use SQLite database
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    os.environ["LACUNA_DATABASE__URL"] = f"sqlite:///{data_dir}/lacuna_dev.db"

    # Disable Redis (use in-memory)
    os.environ["LACUNA_REDIS__ENABLED"] = "false"

    # Disable heavy classifiers
    os.environ["LACUNA_CLASSIFICATION__EMBEDDING_ENABLED"] = "false"
    os.environ["LACUNA_CLASSIFICATION__LLM_ENABLED"] = "false"

    # Disable policy engine
    os.environ["LACUNA_POLICY__ENABLED"] = "false"

    # Disable monitoring
    os.environ["LACUNA_MONITORING__ENABLED"] = "false"

    # Use text logging for readability
    os.environ["LACUNA_LOG_FORMAT"] = "text"
    os.environ["LACUNA_LOG_LEVEL"] = "DEBUG"

    click.echo("🔧 Starting Lacuna in Development Mode")
    click.echo(f"{'=' * 50}")
    click.echo("  Database:    SQLite (data/lacuna_dev.db)")
    click.echo("  Redis:       Disabled (in-memory cache)")
    click.echo("  Classifiers: Heuristic only (fast)")
    click.echo("  Policy:      Disabled")
    click.echo(f"{'=' * 50}")
    click.echo(f"  API:         http://{host}:{port}")
    click.echo(f"  Docs:        http://{host}:{port}/docs")
    click.echo(f"  Admin:       http://{host}:{port}/admin/")
    click.echo(f"  User:        http://{host}:{port}/user/dashboard")
    click.echo(f"{'=' * 50}")

    # Initialize database
    from lacuna.db.base import init_db

    init_db()
    click.echo("✓ Database initialized")

    uvicorn.run(
        "lacuna.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug",
    )


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")  # nosec B104
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option("--reload/--no-reload", default=False, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the Lacuna API server.

    Example:
        lacuna serve --port 8000
    """
    import uvicorn

    click.echo(f"🚀 Starting Lacuna API server on {host}:{port}")
    click.echo(f"   Documentation: http://{host}:{port}/docs")

    uvicorn.run(
        "lacuna.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command()
@click.option("--revision", "-r", help="Target revision")
@click.option("--message", "-m", help="Migration message")
@click.option("--generate/--no-generate", default=False, help="Generate new migration")
def migrate(revision: Optional[str], message: Optional[str], generate: bool) -> None:
    """Run database migrations.

    Example:
        lacuna migrate
        lacuna migrate --generate -m "Add new column"
    """
    # Parameters reserved for future implementation
    _ = (revision, message, generate)
    click.echo("Database migrations not yet implemented.")
    click.echo("Use: alembic upgrade head")


@cli.command()
def config() -> None:
    """Show current configuration."""
    from lacuna.config import get_settings

    settings = get_settings()

    click.echo("\n⚙️ Lacuna Configuration")
    click.echo(f"{'=' * 40}")
    click.echo(f"Version: {__version__}")
    click.echo(f"Environment: {settings.environment}")
    click.echo(f"Debug: {settings.debug}")
    click.echo(f"\nDatabase: {settings.database.url[:50]}...")
    click.echo(f"Redis: {settings.redis.url}")
    click.echo("\nClassification:")
    click.echo(f"  Strategy: {settings.classification.strategy}")
    click.echo(f"  Heuristic: {settings.classification.heuristic_enabled}")
    click.echo(f"  Embedding: {settings.classification.embedding_enabled}")
    click.echo(f"  LLM: {settings.classification.llm_enabled}")
    click.echo(f"\nPolicy Engine: {settings.policy.enabled}")
    click.echo(f"Audit Logging: {settings.audit.enabled}")
    click.echo(f"Lineage Tracking: {settings.lineage.enabled}")


# Register admin commands
cli.add_command(admin_commands, name="admin")


@cli.command()
def stats() -> None:
    """Show governance engine statistics."""
    from lacuna.engine.governance import GovernanceEngine

    engine = GovernanceEngine()

    try:
        stats = engine.get_stats()

        click.echo("\n📊 Governance Engine Statistics")
        click.echo(f"{'=' * 40}")

        click.echo("\nClassifier:")
        for key, value in stats.get("classifier", {}).items():
            click.echo(f"  {key}: {value}")

        click.echo("\nPolicy Engine:")
        for key, value in stats.get("policy_engine", {}).items():
            click.echo(f"  {key}: {value}")

        click.echo("\nLineage Tracker:")
        for key, value in stats.get("lineage_tracker", {}).items():
            click.echo(f"  {key}: {value}")

    finally:
        engine.stop()


def main() -> None:
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
