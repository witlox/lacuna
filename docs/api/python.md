# Python SDK Reference

The Python SDK provides programmatic access to Lacuna's core functionality.

## Installation

```bash
pip install lacuna
```

## Core Modules

### Classification Pipeline

Classify data for sensitivity:

```python
from lacuna.classifier import ClassificationPipeline
from lacuna.models import Classification

# Initialize pipeline
pipeline = ClassificationPipeline()

# Classify a query
classification = pipeline.classify(
    query="Show me all customer emails and SSNs"
)

print(f"Tier: {classification.tier}")  # PROPRIETARY
print(f"Confidence: {classification.confidence}")  # 0.95
print(f"Tags: {classification.tags}")  # ['PII', 'GDPR', 'SSN']
```

#### Custom Configuration

```python
from lacuna.classifier import ClassificationPipeline
from lacuna.config import ClassificationSettings

settings = ClassificationSettings(
    strategy="fast",  # Use only heuristics + embeddings
    confidence_threshold=0.8,
    default_tier="INTERNAL"
)

pipeline = ClassificationPipeline(settings=settings)
```

### Governance Engine

Complete governance workflow:

```python
from lacuna.engine import GovernanceEngine
from lacuna.models import DataOperation, OperationType, UserContext

# Initialize engine
engine = GovernanceEngine()

# Define operation
operation = DataOperation(
    operation_type=OperationType.EXPORT,
    source_resources=["customers.csv"],
    destination_resource="/home/user/Downloads/export.csv",
    user_context=UserContext(
        user_id="analyst@example.com",
        role="data_analyst",
        department="analytics"
    )
)

# Evaluate
result = engine.evaluate(operation)

if result.allowed:
    print("Operation allowed")
else:
    print(f"Operation denied: {result.reasoning}")
    print("Alternatives:")
    for alt in result.alternatives:
        print(f"  - {alt}")
```

### Lineage Tracker

Track data dependencies:

```python
from lacuna.lineage import LineageTracker
from lacuna.models import DataOperation, OperationType

tracker = LineageTracker()

# Track an operation
operation = DataOperation(
    operation_type=OperationType.TRANSFORM,
    source_resources=["customers.csv", "sales.csv"],
    destination_resource="customer_analysis.csv"
)
tracker.track(operation)

# Query lineage
lineage = tracker.get_lineage("customer_analysis.csv")
print(lineage.to_graph())

# Get upstream dependencies
upstream = tracker.get_upstream("customer_analysis.csv", max_depth=5)
print(f"Depends on {len(upstream)} resources")

# Get downstream impact
downstream = tracker.get_downstream("customers.csv")
print(f"Impacts {len(downstream)} resources")
```

### Policy Engine

Evaluate operations against policies:

```python
from lacuna.policy import PolicyEngine
from lacuna.models import DataTier, UserContext

engine = PolicyEngine()

# Evaluate export
allowed = engine.evaluate_export(
    data_tier=DataTier.PROPRIETARY,
    destination="/home/user/Downloads/export.csv",
    user_context=UserContext(
        user_id="analyst@example.com",
        role="data_analyst"
    )
)

print(f"Export allowed: {allowed}")
```

### Audit Logger

Query audit logs:

```python
from lacuna.audit import AuditLogger
from datetime import datetime, timedelta

logger = AuditLogger()

# Query logs
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

logs = logger.query(
    user_id="analyst@example.com",
    start_date=start_date,
    end_date=end_date,
    operation_types=["READ", "EXPORT"],
    limit=100
)

for log in logs:
    print(f"{log.timestamp}: {log.operation_type} on {log.resource}")
```

## Data Models

### Classification

```python
from lacuna.models import Classification, DataTier

classification = Classification(
    tier=DataTier.PROPRIETARY,
    confidence=0.95,
    tags=["PII", "GDPR"],
    reasoning="Contains personally identifiable information"
)
```

**Fields:**

- `tier` - DataTier enum (PROPRIETARY, INTERNAL, PUBLIC)
- `confidence` - float (0.0 to 1.0)
- `tags` - List of classification tags
- `reasoning` - String explaining the classification

### DataOperation

```python
from lacuna.models import DataOperation, OperationType, UserContext

operation = DataOperation(
    operation_type=OperationType.READ,
    source_resources=["customers.csv"],
    destination_resource="analysis.csv",
    user_context=UserContext(
        user_id="analyst@example.com",
        role="data_analyst",
        department="analytics",
        clearance_level=2
    ),
    purpose="Customer segmentation analysis"
)
```

**OperationType Enum:**

- `READ` - Read data
- `WRITE` - Write data
- `DELETE` - Delete data
- `EXPORT` - Export to external location
- `QUERY` - Query database
- `TRANSFORM` - Transform data
- `JOIN` - Join datasets
- `AGGREGATE` - Aggregate data

### UserContext

```python
from lacuna.models import UserContext

context = UserContext(
    user_id="analyst@example.com",
    role="data_analyst",
    department="analytics",
    clearance_level=2,
    session_id="session-123",
    ip_address="192.168.1.100"
)
```

### GovernanceResult

```python
from lacuna.engine import GovernanceEngine

result = engine.evaluate(operation)

# Fields
print(result.allowed)  # bool
print(result.reasoning)  # str
print(result.classification)  # Classification
print(result.policy_evaluation)  # PolicyEvaluation
print(result.alternatives)  # List[str]
print(result.latency_ms)  # float
```

## Custom Classifiers

Extend the classification pipeline with custom logic:

```python
from lacuna.classifier.base import Classifier
from lacuna.models import Classification, DataTier

class CustomClassifier(Classifier):
    """Custom classifier for company-specific patterns."""

    def __init__(self):
        super().__init__(priority=55)  # Between heuristic and embedding

    def classify(self, query: str, **kwargs) -> Classification:
        # Custom classification logic
        if "project apollo" in query.lower():
            return Classification(
                tier=DataTier.PROPRIETARY,
                confidence=1.0,
                tags=["PROJECT_APOLLO", "CONFIDENTIAL"],
                reasoning="Mentions classified project name"
            )

        # Return None if can't classify
        return None

# Add to pipeline
from lacuna.classifier import ClassificationPipeline

pipeline = ClassificationPipeline()
pipeline.add_classifier(CustomClassifier())
```

## Configuration

### Settings

```python
from lacuna.config import Settings

settings = Settings(
    database_url="postgresql://user:pass@localhost/lacuna",
    redis_url="redis://localhost:6379/0",
    opa_url="http://localhost:8181",
    classification=ClassificationSettings(
        strategy="comprehensive",
        confidence_threshold=0.75,
        cache_ttl=300
    ),
    lineage=LineageSettings(
        max_depth=10,
        enable_tag_propagation=True
    ),
    audit=AuditSettings(
        retention_days=2555  # 7 years
    )
)
```

### Environment Variables

```python
import os
from lacuna.config import Settings

# Set environment variables
os.environ["DATABASE_URL"] = "postgresql://..."
os.environ["REDIS_URL"] = "redis://..."

# Settings will auto-load from environment
settings = Settings()
```

## Async Support

Most operations support async execution:

```python
import asyncio
from lacuna.classifier import AsyncClassificationPipeline

async def classify_batch():
    pipeline = AsyncClassificationPipeline()

    queries = [
        "Show me customer emails",
        "Get sales data",
        "Export financial reports"
    ]

    # Classify concurrently
    tasks = [pipeline.classify(q) for q in queries]
    results = await asyncio.gather(*tasks)

    for query, result in zip(queries, results):
        print(f"{query}: {result.tier}")

# Run
asyncio.run(classify_batch())
```

## Error Handling

```python
from lacuna.exceptions import (
    ClassificationError,
    PolicyViolation,
    LineageError,
    AuditError
)

try:
    result = engine.evaluate(operation)
except PolicyViolation as e:
    print(f"Policy violation: {e.message}")
    print(f"Policy: {e.policy_id}")
    print(f"Alternatives: {e.alternatives}")
except ClassificationError as e:
    print(f"Classification failed: {e.message}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Examples

See the [`examples/`](https://github.com/witlox/lacuna/tree/main/examples) directory for complete examples:

- `basic_classification.py` - Simple classification
- `governance_workflow.py` - Complete governance workflow
- `lineage_tracking.py` - Lineage tracking
- `audit_logging.py` - Audit log queries
- `custom_classifier.py` - Custom classifier implementation
- `batch_classification.py` - Batch operations

## Next Steps

- **[REST API Reference](rest.md)** - HTTP API documentation
- **[Plugin Development](../PLUGINS.md)** - Extend Lacuna
- **[Integration Guide](../INTEGRATIONS.md)** - Platform integrations
