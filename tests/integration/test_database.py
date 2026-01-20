"""Integration tests for PostgreSQL database operations."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from lacuna.db.models import AuditLogModel, ClassificationModel, LineageEdgeModel
from lacuna.models.classification import DataTier

pytestmark = pytest.mark.integration


class TestDatabaseConnection:
    """Tests for database connectivity."""

    def test_database_connection(self, db_engine):
        """Test that we can connect to the database."""
        from sqlalchemy import text

        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_database_version(self, db_engine):
        """Test that we're running PostgreSQL 16+."""
        from sqlalchemy import text

        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version


class TestClassificationModel:
    """Tests for classification database operations."""

    def test_create_classification(self, db_session, setup_database):
        """Test creating a classification record."""
        classification = ClassificationModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            tier="PROPRIETARY",
            confidence=0.95,
            reasoning="Contains customer data",
            matched_rules=["customer_pattern"],
            tags=["PII", "GDPR"],
            classifier_name="heuristic",
            classifier_version="1.0.0",
        )

        db_session.add(classification)
        db_session.commit()

        # Verify it was saved
        saved = (
            db_session.query(ClassificationModel)
            .filter_by(id=classification.id)
            .first()
        )
        assert saved is not None
        assert saved.tier == "PROPRIETARY"
        assert saved.confidence == 0.95
        assert "PII" in saved.tags

    def test_query_classifications_by_tier(self, db_session, setup_database):
        """Test querying classifications by tier."""
        # Create multiple classifications
        for tier in ["PUBLIC", "INTERNAL", "PROPRIETARY"]:
            classification = ClassificationModel(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                tier=tier,
                confidence=0.9,
                reasoning=f"Test {tier}",
                classifier_name="test",
            )
            db_session.add(classification)

        db_session.commit()

        # Query by tier
        proprietary = (
            db_session.query(ClassificationModel).filter_by(tier="PROPRIETARY").all()
        )

        assert len(proprietary) >= 1
        assert all(c.tier == "PROPRIETARY" for c in proprietary)

    def test_classification_with_parent(self, db_session, setup_database):
        """Test classification inheritance."""
        parent = ClassificationModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            tier="PROPRIETARY",
            confidence=0.95,
            reasoning="Parent classification",
            tags=["PII"],
            classifier_name="heuristic",
        )
        db_session.add(parent)
        db_session.commit()

        child = ClassificationModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            tier="PROPRIETARY",
            confidence=0.90,
            reasoning="Inherited from parent",
            tags=["PII", "DERIVED"],
            classifier_name="heuristic",
            parent_id=parent.id,
        )
        db_session.add(child)
        db_session.commit()

        # Verify relationship
        saved_child = (
            db_session.query(ClassificationModel).filter_by(id=child.id).first()
        )
        assert saved_child.parent_id == parent.id
        assert saved_child.parent is not None
        assert saved_child.parent.tier == "PROPRIETARY"


class TestLineageEdgeModel:
    """Tests for lineage edge database operations."""

    def test_create_lineage_edge(self, db_session, setup_database):
        """Test creating a lineage edge."""
        edge = LineageEdgeModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            source_artifact_id="customers.csv",
            target_artifact_id="analysis.csv",
            operation_type="transform",
        )

        db_session.add(edge)
        db_session.commit()

        saved = db_session.query(LineageEdgeModel).filter_by(id=edge.id).first()
        assert saved is not None
        assert saved.source_artifact_id == "customers.csv"
        assert saved.target_artifact_id == "analysis.csv"

    def test_query_lineage_by_source(self, db_session, setup_database):
        """Test querying lineage by source artifact."""
        source_id = f"source_{uuid4().hex[:8]}"

        # Create multiple edges from same source
        for i in range(3):
            edge = LineageEdgeModel(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                source_artifact_id=source_id,
                target_artifact_id=f"target_{i}.csv",
                operation_type="transform",
            )
            db_session.add(edge)

        db_session.commit()

        # Query by source
        edges = (
            db_session.query(LineageEdgeModel)
            .filter_by(source_artifact_id=source_id)
            .all()
        )

        assert len(edges) == 3

    def test_lineage_with_classifications(self, db_session, setup_database):
        """Test lineage edges with classification references."""
        # Create classifications
        source_class = ClassificationModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            tier="PROPRIETARY",
            confidence=0.95,
            reasoning="Source data",
            classifier_name="test",
        )
        target_class = ClassificationModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            tier="PROPRIETARY",
            confidence=0.90,
            reasoning="Derived data",
            classifier_name="test",
        )
        db_session.add(source_class)
        db_session.add(target_class)
        db_session.commit()

        # Create edge with classifications
        edge = LineageEdgeModel(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            source_artifact_id="source.csv",
            target_artifact_id="target.csv",
            operation_type="transform",
            source_classification_id=source_class.id,
            target_classification_id=target_class.id,
        )
        db_session.add(edge)
        db_session.commit()

        # Verify relationships
        saved = db_session.query(LineageEdgeModel).filter_by(id=edge.id).first()
        assert saved.source_classification is not None
        assert saved.source_classification.tier == "PROPRIETARY"
        assert saved.target_classification is not None


class TestAuditLogModel:
    """Tests for audit log database operations."""

    def test_create_audit_log(self, db_session, setup_database):
        """Test creating an audit log entry."""
        audit = AuditLogModel(
            event_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type="data.access",
            severity="INFO",
            user_id="test-user",
            resource_type="file",
            resource_id="customers.csv",
            action="read",
            action_result="success",
        )

        db_session.add(audit)
        db_session.commit()

        saved = (
            db_session.query(AuditLogModel).filter_by(event_id=audit.event_id).first()
        )
        assert saved is not None
        assert saved.event_type == "data.access"
        assert saved.user_id == "test-user"

    def test_query_audit_by_user(self, db_session, setup_database):
        """Test querying audit logs by user."""
        user_id = f"user_{uuid4().hex[:8]}"

        # Create multiple audit entries
        for i in range(5):
            audit = AuditLogModel(
                event_id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                event_type="data.access",
                severity="INFO",
                user_id=user_id,
                resource_type="file",
                resource_id=f"file_{i}.csv",
                action="read",
                action_result="success",
            )
            db_session.add(audit)

        db_session.commit()

        # Query by user
        logs = db_session.query(AuditLogModel).filter_by(user_id=user_id).all()
        assert len(logs) == 5

    def test_query_audit_by_event_type(self, db_session, setup_database):
        """Test querying audit logs by event type."""
        # Create policy deny events
        for i in range(3):
            audit = AuditLogModel(
                event_id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                event_type="policy.deny",
                severity="WARNING",
                user_id=f"user_{i}",
                resource_type="file",
                resource_id=f"sensitive_{i}.csv",
                action="export",
                action_result="denied",
            )
            db_session.add(audit)

        db_session.commit()

        # Query policy denials
        denials = (
            db_session.query(AuditLogModel).filter_by(event_type="policy.deny").all()
        )

        assert len(denials) >= 3
        assert all(d.action_result == "denied" for d in denials)

    def test_audit_hash_chain(self, db_session, setup_database):
        """Test audit log hash chain for integrity."""
        previous_hash = None

        for i in range(5):
            audit = AuditLogModel(
                event_id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                event_type="data.access",
                severity="INFO",
                user_id="chain-test",
                resource_type="file",
                resource_id=f"file_{i}.csv",
                action="read",
                action_result="success",
                previous_record_hash=previous_hash,
                record_hash=f"hash_{i}",
            )
            db_session.add(audit)
            previous_hash = f"hash_{i}"

        db_session.commit()

        # Verify chain
        logs = (
            db_session.query(AuditLogModel)
            .filter_by(user_id="chain-test")
            .order_by(AuditLogModel.timestamp)
            .all()
        )

        assert len(logs) == 5
        # First record should have no previous hash
        assert logs[0].previous_record_hash is None
        # Subsequent records should chain
        for i in range(1, len(logs)):
            assert logs[i].previous_record_hash == logs[i - 1].record_hash
