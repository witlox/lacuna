# Lacuna Examples

This directory contains example scripts demonstrating various Lacuna features.

## Prerequisites

All examples assume you have Lacuna installed and are running in dev mode:

```bash
# Install lacuna
pip install -e .

# Start dev mode (uses SQLite, in-memory backends)
lacuna dev
```

## Examples

### Basic Usage

| Example | Description |
|---------|-------------|
| `basic_classification.py` | Classify data and check sensitivity tiers |
| `policy_evaluation.py` | Evaluate operations against policies |
| `lineage_tracking.py` | Track data lineage and provenance |
| `audit_logging.py` | Query and inspect audit logs |

### API Integration

| Example | Description |
|---------|-------------|
| `api_client.py` | HTTP client for the REST API |
| `batch_classification.py` | Classify multiple items efficiently |

### Advanced

| Example | Description |
|---------|-------------|
| `custom_classifier.py` | Create a custom classification rule |
| `governance_workflow.py` | Complete governance workflow example |

## Running Examples

Each example can be run directly:

```bash
# Make sure dev server is running in another terminal
lacuna dev

# Run an example
python examples/basic_classification.py
```

Or import components in your own code:

```python
from lacuna.engine.governance import GovernanceEngine

engine = GovernanceEngine()
result = engine.classify("SELECT * FROM customers")
print(f"Classification: {result.tier}")
```
