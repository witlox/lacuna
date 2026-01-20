"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-19

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create classifications table
    op.create_table(
        "classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("tier", sa.String(20), nullable=False, index=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("matched_rules", postgresql.ARRAY(sa.String()), default=list),
        sa.Column("tags", postgresql.ARRAY(sa.String()), default=list, index=True),
        sa.Column("classifier_name", sa.String(100), nullable=False),
        sa.Column("classifier_version", sa.String(50)),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("classifications.id"),
        ),
        sa.Column("metadata", postgresql.JSON(), default=dict),
    )

    op.create_index(
        "idx_classification_tier_timestamp", "classifications", ["tier", "timestamp"]
    )

    # Create lineage_edges table
    op.create_table(
        "lineage_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("source_artifact_id", sa.String(500), nullable=False, index=True),
        sa.Column("target_artifact_id", sa.String(500), nullable=False, index=True),
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column(
            "source_classification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("classifications.id"),
        ),
        sa.Column(
            "target_classification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("classifications.id"),
        ),
        sa.Column("metadata", postgresql.JSON(), default=dict),
    )

    op.create_index(
        "idx_lineage_source", "lineage_edges", ["source_artifact_id", "timestamp"]
    )

    op.create_index(
        "idx_lineage_target", "lineage_edges", ["target_artifact_id", "timestamp"]
    )

    # Create audit_log table (ISO 27001 compliant)
    op.create_table(
        "audit_log",
        # Core identity
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        # Actor identification
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("user_session_id", sa.String(255)),
        sa.Column("user_ip_address", postgresql.INET()),
        sa.Column("user_role", sa.String(100)),
        sa.Column("user_department", sa.String(100)),
        # Target resource
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(500), nullable=False, index=True),
        sa.Column("resource_classification", sa.String(20), index=True),
        sa.Column("resource_tags", postgresql.ARRAY(sa.String()), default=list),
        # Action details
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("action_result", sa.String(20), nullable=False, index=True),
        sa.Column("action_metadata", postgresql.JSON(), default=dict),
        # Policy/Governance
        sa.Column("policy_id", sa.String(100)),
        sa.Column("policy_version", sa.String(50)),
        sa.Column("classification_tier", sa.String(20)),
        sa.Column("classification_confidence", sa.Float()),
        sa.Column("classification_reasoning", sa.Text()),
        # Lineage/Provenance
        sa.Column(
            "parent_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_log.event_id"),
        ),
        sa.Column("lineage_chain", postgresql.ARRAY(sa.String()), default=list),
        # Compliance metadata
        sa.Column("compliance_flags", postgresql.ARRAY(sa.String()), default=list),
        sa.Column("retention_period_days", sa.Integer(), default=2555),
        # Tamper detection (hash chain)
        sa.Column("previous_record_hash", sa.String(64)),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.Column("signature", sa.Text()),
        # System context
        sa.Column("system_id", sa.String(100)),
        sa.Column("system_version", sa.String(50)),
    )

    # Create indexes for audit_log
    op.create_index("idx_audit_user_timestamp", "audit_log", ["user_id", "timestamp"])
    op.create_index(
        "idx_audit_resource_timestamp", "audit_log", ["resource_id", "timestamp"]
    )
    op.create_index(
        "idx_audit_classification_timestamp",
        "audit_log",
        ["resource_classification", "timestamp"],
    )
    op.create_index("idx_audit_event_type", "audit_log", ["event_type", "timestamp"])
    op.create_index(
        "idx_audit_action_result", "audit_log", ["action_result", "timestamp"]
    )

    # Create policy_evaluations table
    op.create_table(
        "policy_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("policy_id", sa.String(100), nullable=False, index=True),
        sa.Column("policy_version", sa.String(50)),
        sa.Column("policy_name", sa.String(255)),
        sa.Column("allowed", sa.String(20), nullable=False, index=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("resource_id", sa.String(500), nullable=False),
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column(
            "classification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("classifications.id"),
        ),
        sa.Column("evaluation_duration_ms", sa.Float()),
        sa.Column("alternatives", postgresql.JSON(), default=list),
        sa.Column("metadata", postgresql.JSON(), default=dict),
    )

    op.create_index(
        "idx_policy_eval_user", "policy_evaluations", ["user_id", "timestamp"]
    )
    op.create_index(
        "idx_policy_eval_resource", "policy_evaluations", ["resource_id", "timestamp"]
    )
    op.create_index(
        "idx_policy_eval_result", "policy_evaluations", ["allowed", "timestamp"]
    )


def downgrade() -> None:
    op.drop_table("policy_evaluations")
    op.drop_table("audit_log")
    op.drop_table("lineage_edges")
    op.drop_table("classifications")
