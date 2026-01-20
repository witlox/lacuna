# Quick Start

Get Lacuna running in minutes with development mode or deploy to production.

## Development Mode

The fastest way to try Lacuna locally with zero external dependencies:

### Prerequisites

- Python 3.9 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/witlox/lacuna.git
cd lacuna

# Install in development mode
pip install -e .
```

### Start the Server

```bash
# Start in dev mode (uses SQLite, no external dependencies)
lacuna dev
```

This starts Lacuna with:

- SQLite database (no PostgreSQL needed)
- In-memory cache (no Redis needed)
- Built-in policies (no OPA needed)
- Auto-reload on code changes

### Access the Interfaces

Once started, you can access:

- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **User Dashboard**: [http://127.0.0.1:8000/user/dashboard](http://127.0.0.1:8000/user/dashboard)
- **Admin Dashboard**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## Your First Classification

Try classifying some data using the Python SDK:

```python
from lacuna.classifier import ClassificationPipeline
from lacuna.models import Classification

# Initialize the classifier
pipeline = ClassificationPipeline()

# Classify a query
query = "Show me all customer emails and social security numbers"
classification = pipeline.classify(query)

print(f"Tier: {classification.tier}")
print(f"Confidence: {classification.confidence}")
print(f"Tags: {classification.tags}")
print(f"Reasoning: {classification.reasoning}")
```

Expected output:

```
Tier: PROPRIETARY
Confidence: 0.95
Tags: ['PII', 'GDPR', 'SSN']
Reasoning: Contains personally identifiable information (email, SSN)
```

## Track Lineage

Track data dependencies through operations:

```python
from lacuna.lineage import LineageTracker
from lacuna.models import DataOperation, OperationType, UserContext

# Initialize tracker
tracker = LineageTracker()

# Record a data operation
operation = DataOperation(
    operation_type=OperationType.READ,
    source_resources=["customers.csv"],
    destination_resource="customer_analysis.csv",
    user_context=UserContext(
        user_id="analyst@example.com",
        role="data_analyst",
        department="analytics"
    )
)

# Track the operation
tracker.track(operation)

# Query lineage
lineage = tracker.get_lineage("customer_analysis.csv")
print(lineage.to_graph())
```

## Evaluate Policies

Check if an operation is allowed:

```python
from lacuna.engine import GovernanceEngine
from lacuna.models import DataOperation, OperationType, UserContext

# Initialize engine
engine = GovernanceEngine()

# Define an operation
operation = DataOperation(
    operation_type=OperationType.EXPORT,
    source_resources=["customers.csv"],
    destination_resource="/home/user/Downloads/export.csv",
    user_context=UserContext(
        user_id="analyst@example.com",
        role="data_analyst"
    )
)

# Evaluate
result = engine.evaluate(operation)

print(f"Allowed: {result.allowed}")
print(f"Reasoning: {result.reasoning}")
if not result.allowed and result.alternatives:
    print("Alternatives:")
    for alt in result.alternatives:
        print(f"  - {alt}")
```

## Run the Examples

The `examples/` directory contains runnable scripts:

```bash
# Start the dev server in the background
lacuna dev &

# Run examples
python examples/basic_classification.py
python examples/lineage_tracking.py
python examples/policy_evaluation.py
python examples/audit_logging.py
```

## Next Steps

- **[User Guide](../USER_GUIDE.md)** - Learn about all features
- **[Architecture](../ARCHITECTURE.md)** - Understand how it works
- **[Deployment Guide](../DEPLOYMENT.md)** - Deploy to production
- **[Development Guide](../DEVELOPMENT.md)** - Contribute to Lacuna

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
lacuna dev --port 8001
```

### Import Errors

Make sure you installed in development mode:

```bash
pip install -e .
```

### Database Issues

Development mode uses SQLite. If you encounter database issues:

```bash
# Remove the dev database
rm lacuna_dev.db

# Restart
lacuna dev
```

For more help, see the [User Guide](../USER_GUIDE.md) or [open an issue](https://github.com/witlox/lacuna/issues).
