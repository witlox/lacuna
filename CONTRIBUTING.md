# Contributing to Lacuna

Thank you for your interest in contributing! This is a data governance and lineage tracking project focused on enabling self-service data access while maintaining compliance and policy enforcement.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)

## Code of Conduct

### Our Pledge

We pledge to make participation in this project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Harassment, trolling, or discriminatory comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## Getting Started

### Areas We Need Help

🔐 **Classification Pipeline**
- Improve heuristics for common data patterns
- Add embedding models for semantic classification
- Optimize LLM prompts for context-aware decisions
- Add support for custom data types

📊 **Lineage Tracking**
- Track lineage across SQL transformations
- Support for complex joins and aggregations
- Integration with dbt lineage graphs
- Visualization improvements

🛡️ **Policy Engine**
- OPA policy templates for common use cases
- Policy testing framework
- Integration with external policy systems
- Real-time policy evaluation optimization

📚 **Documentation**
- Examples and tutorials
- Architecture decision records
- Best practices guides
- Integration guides for various platforms

🎨 **Tooling**
- IDE plugins (VS Code, PyCharm)
- Jupyter notebook integration improvements
- Web dashboard features
- CLI enhancements

🔍 **Audit & Compliance**
- ISO 27001 report generators
- GDPR compliance utilities
- HIPAA audit trail support
- Retention policy automation

🔌 **Integrations**
- Databricks Unity Catalog integration
- Snowflake governance features
- AWS Lake Formation support
- Azure Purview connectors

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Optional: PostgreSQL 14+ (for production mode)
- Optional: Docker (for containerized deployment)

### Clone Repository

```bash
git clone https://github.com/witlox/lacuna.git
cd lacuna
```

### Python Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Quick Start with Dev Mode

The fastest way to run Lacuna locally is dev mode, which uses SQLite and in-memory backends:

```bash
# Start in dev mode (no external dependencies required)
lacuna dev

# Open in browser
# API Docs: http://127.0.0.1:8000/docs
# User Dashboard: http://127.0.0.1:8000/user/dashboard
# Admin Dashboard: http://127.0.0.1:8000/admin/
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development setup.

### Full Production Setup (Optional)

For testing with production-like services:

```bash
# Database Setup
createdb lacuna_dev

# Run migrations
alembic upgrade head

# OPA (Open Policy Agent) Setup
brew install opa  # macOS
# Or download from https://www.openpolicyagent.org/docs/latest/#running-opa

# Start with full services
lacuna serve --reload
```

### Verify Installation

```bash
# Test CLI
lacuna --version

# Run example classification
lacuna classify --file examples/sample_data.csv
```

## How to Contribute

### 1. Find an Issue

Browse [open issues](https://github.com/witlox/lacuna/issues) or create a new one.

**Good first issues are labeled:** `good-first-issue`, `help-wanted`, `documentation`

### 2. Discuss Your Approach

For significant changes:
1. Create an issue first
2. Discuss the approach
3. Get feedback before coding

For small fixes (typos, bugs):
- Just submit a PR

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

**Branch naming:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `test/` - Test improvements
- `refactor/` - Code refactoring

### 4. Make Changes

Follow our [coding standards](#coding-standards) and write tests.

### 5. Commit

Use clear, descriptive commit messages:

```bash
git commit -m "feat: add PII detection to classification pipeline"
git commit -m "fix: handle lineage tracking for complex SQL joins"
git commit -m "docs: add example for policy enforcement workflow"
```

**Commit message format:**
```
type: short description

Longer explanation if needed.

Fixes #123
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `test` - Tests
- `refactor` - Code refactoring
- `perf` - Performance improvement
- `chore` - Maintenance

### 6. Push and Create PR

```bash
git push origin your-branch-name
```

Then create a Pull Request on GitHub.

## Pull Request Process

### PR Checklist

Before submitting, ensure:

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Tests pass (`pytest` for Python, `cargo test` for Rust)
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Related Issues
Fixes #123

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Follows coding standards
```

### Review Process

1. **Automated checks run** (tests, linting, type checking)
2. **Maintainer reviews** (usually within 2-3 days)
3. **Address feedback**
4. **Approval & merge**

## Coding Standards

### Python

**Style Guide:** PEP 8 with modifications

```python
# Good
def classify_data_operation(
    operation: DataOperation,
    context: ClassificationContext,
    use_llm: bool = False
) -> ClassificationResult:
    """
    Classify a data operation using the three-layer pipeline.

    Args:
        operation: The data operation to classify (read, write, export, etc.)
        context: Contextual information (user, lineage, conversation)
        use_llm: Whether to use LLM layer for complex decisions

    Returns:
        ClassificationResult with tier, tags, and confidence

    Raises:
        ValidationError: If operation data is invalid
        ClassificationError: If classification fails
    """
    # Implementation
    pass

# Bad
def classify(op, ctx, llm=False):  # No type hints, unclear names
    pass
```

**Key points:**
- Type hints required (Python 3.10+ syntax)
- Docstrings for all public functions (Google style)
- Max line length: 100 characters
- Use `black` for formatting
- Use `mypy` for type checking
- Use `ruff` for linting

**Run formatters:**
```bash
black python/
ruff check python/
mypy python/
```

### OPA (Open Policy Agent) Policies

**Style Guide:** Rego best practices

```rego
# Good - clear, well-documented policy
package lacuna.policies.pii_export

import future.keywords.if
import future.keywords.in

# Deny PII exports to unmanaged locations
deny[msg] if {
    input.operation.type == "export"
    input.data.classification.tier == "PROPRIETARY"
    "PII" in input.data.tags
    not is_managed_location(input.operation.destination)

    msg := sprintf(
        "Cannot export PII data to unmanaged location: %s",
        [input.operation.destination]
    )
}

# Helper: Check if destination is managed
is_managed_location(path) if {
    startswith(path, "/governed/")
}

# Bad - unclear, no documentation
deny[msg] if {
    input.op.t == "exp"
    input.d.c == "P"
    msg := "denied"
}
```

**Key points:**
- Use descriptive package names
- Document policy intent and rules
- Use helper functions for clarity
- Include examples in comments
- Test policies with sample data

**Run tests:**
```bash
opa test policies/
```

### SQL & Database

```sql
-- Good - properly structured migration
-- Migration: 2025_01_add_lineage_tracking
-- Description: Add lineage tracking tables for data operations

CREATE TABLE IF NOT EXISTS lineage_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_artifact_id UUID NOT NULL REFERENCES artifacts(id),
    target_artifact_id UUID NOT NULL REFERENCES artifacts(id),
    operation_type VARCHAR(50) NOT NULL,  -- 'transform', 'join', 'export', etc.
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    CONSTRAINT unique_lineage_edge UNIQUE (source_artifact_id, target_artifact_id, operation_type)
);

CREATE INDEX idx_lineage_source ON lineage_edges(source_artifact_id);
CREATE INDEX idx_lineage_target ON lineage_edges(target_artifact_id);

-- Bad - unclear structure, no constraints
CREATE TABLE lineage (
    id SERIAL,
    src TEXT,
    dst TEXT,
    op TEXT
);
```

**Key points:**
- Use descriptive table and column names
- Add comments explaining purpose
- Include appropriate constraints and indexes
- Use proper data types (UUID, TIMESTAMP, JSONB)
- Follow migration naming conventions

## Testing Requirements

### Test Coverage

- **Minimum:** 80% code coverage
- **Target:** 90%+ for critical paths
- **Required:** 100% for contract validation

### Test Types

**1. Unit Tests**

Test individual functions:

```python
def test_pii_classifier_detection():
    """Test PII detection in data classification"""
    classifier = PIIClassifier()

    # Valid case - should detect PII
    result = classifier.classify_dataframe(
        df=pd.DataFrame({"email": ["user@example.com"], "name": ["John Doe"]}),
        context={}
    )
    assert "PII" in result.tags
    assert result.tier == DataTier.PROPRIETARY

    # Invalid case - no PII
    result = classifier.classify_dataframe(
        df=pd.DataFrame({"count": [100], "category": ["A"]}),
        context={}
    )
    assert "PII" not in result.tags
```

**2. Integration Tests**

Test components together:

```python
def test_policy_enforcement_end_to_end():
    """Test complete policy enforcement pipeline"""
    # Create test data with PII
    test_df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "email": ["test@example.com", "user@example.com", "admin@example.com"],
        "purchase_amount": [100.0, 200.0, 150.0]
    })

    # Classify data
    classifier = DataClassifier()
    classification = classifier.classify(test_df)
    assert classification.tier == DataTier.PROPRIETARY

    # Try to export (should be blocked)
    policy_engine = PolicyEngine()
    result = policy_engine.evaluate_operation(
        operation=DataOperation(type="export", destination="~/Downloads/data.csv"),
        classification=classification,
        user=User(role="analyst")
    )

    assert result.allowed is False
    assert "PII" in result.reason
    assert len(result.alternatives) > 0
```

**3. Lineage Validation Tests**

Validate lineage tracking across operations:

```python
def test_lineage_propagation_through_joins():
    """Test that classification propagates correctly through joins"""
    # Create proprietary data
    customers = pd.DataFrame({"customer_id": [1, 2], "email": ["a@b.com", "c@d.com"]})
    customers_classified = classify_dataframe(customers, tier=DataTier.PROPRIETARY)

    # Create internal data
    orders = pd.DataFrame({"customer_id": [1, 2], "amount": [100, 200]})
    orders_classified = classify_dataframe(orders, tier=DataTier.INTERNAL)

    # Join operation
    lineage_tracker = LineageTracker()
    result = customers_classified.merge(orders_classified, on="customer_id")

    # Verify lineage tracking
    lineage = lineage_tracker.get_lineage(result.artifact_id)
    assert len(lineage.sources) == 2
    assert customers_classified.artifact_id in lineage.sources
    assert orders_classified.artifact_id in lineage.sources

    # Verify classification propagation (should inherit highest tier)
    assert result.classification.tier == DataTier.PROPRIETARY
```

**4. Property-Based Tests**

Test invariants:

```python
from hypothesis import given, strategies as st

@given(
    tier1=st.sampled_from([DataTier.PUBLIC, DataTier.INTERNAL, DataTier.PROPRIETARY]),
    tier2=st.sampled_from([DataTier.PUBLIC, DataTier.INTERNAL, DataTier.PROPRIETARY])
)
def test_classification_propagation_invariant(tier1, tier2):
    """Property: Classification always inherits highest tier"""
    # Create two dataframes with different tiers
    df1 = pd.DataFrame({"id": [1, 2], "value": [100, 200]})
    df1_classified = classify_dataframe(df1, tier=tier1)

    df2 = pd.DataFrame({"id": [1, 2], "amount": [10, 20]})
    df2_classified = classify_dataframe(df2, tier=tier2)

    # Merge them
    result = df1_classified.merge(df2_classified, on="id")

    # Result should have the highest tier
    expected_tier = max(tier1, tier2, key=lambda t: t.value)
    assert result.classification.tier == expected_tier

@given(operation=st.text(min_size=1))
def test_audit_log_immutability(operation):
    """Property: Audit log entries are immutable once written"""
    logger = AuditLogger()

    # Create audit entry
    entry_id = logger.log_operation(operation_type=operation, user="test_user")

    # Retrieve entry
    entry1 = logger.get_entry(entry_id)

    # Attempt to modify (should fail or create new entry)
    with pytest.raises(ImmutabilityError):
        logger.modify_entry(entry_id, operation_type="modified")

    # Verify entry unchanged
    entry2 = logger.get_entry(entry_id)
    assert entry1 == entry2
```

### Running Tests

```bash
# All tests
pytest                                  # All tests
pytest -v                               # Verbose
pytest --cov=lacuna                     # With coverage
pytest -k test_classification           # Specific tests
pytest -m integration                   # Integration tests only
pytest -m "not slow"                    # Skip slow tests

# Policy tests
opa test policies/                      # Test OPA policies
opa test -v policies/                   # Verbose policy tests

# Database migrations
alembic upgrade head                    # Apply migrations
alembic downgrade -1                    # Rollback one migration
pytest tests/test_migrations.py         # Test migrations
```

### Test Organization

```
tests/
├── unit/
│   ├── test_classification.py
│   ├── test_lineage.py
│   ├── test_policy_engine.py
│   └── test_audit_logger.py
├── integration/
│   ├── test_end_to_end.py
│   ├── test_cli.py
│   └── test_jupyter_integration.py
├── lineage/
│   ├── test_lineage_propagation.py
│   └── test_tag_inheritance.py
├── property/
│   └── test_invariants.py
├── policies/
│   ├── test_pii_policies.py
│   └── test_export_policies.py
└── fixtures/
    ├── sample_data/
    │   ├── customers.csv
    │   ├── transactions.csv
    │   └── public_data.csv
    ├── policies/
    │   ├── pii_export.rego
    │   └── test_policies.rego
    └── expected_classifications/
        └── expected_results.json
```

## Documentation

### What to Document

**Code changes:**
- Update relevant .md files in docs/
- Add docstrings to new functions
- Update API documentation

**New features:**
- Add usage examples to README.md
- Create example in examples/
- Update docs/ARCHITECTURE.md if needed
- Document new policies in docs/POLICY_AS_CODE.md
- Add to CHANGELOG.md

**New integrations:**
- Add to docs/INTEGRATIONS.md
- Include setup instructions
- Provide example configurations

**Bug fixes:**
- Note in commit message
- Add regression test
- Update known issues if applicable

### Documentation Style

**Markdown files:**
- Use clear headings
- Include code examples
- Add cross-references
- Keep examples up-to-date

**Code comments:**
```python
# Good: Explain WHY, not WHAT
# Use three-layer pipeline to balance speed (<10ms for 98%) with accuracy
classification = self._classify_with_fallback(operation, context)

# Bad: State the obvious
# Classify the operation
classification = self._classify_with_fallback(operation, context)
```

**Docstrings:**
```python
def classify_data_operation(
    operation: DataOperation,
    context: ClassificationContext
) -> ClassificationResult:
    """
    Classify a data operation using the three-layer pipeline.

    This function uses heuristics, embeddings, and LLM reasoning
    to determine data sensitivity tier and applicable tags.

    Args:
        operation: The data operation to classify (read, write, export, etc.)
        context: Contextual information including user, lineage, and conversation

    Returns:
        ClassificationResult with tier, tags, confidence, and reasoning

    Raises:
        ValidationError: If operation data is invalid
        ClassificationError: If classification pipeline fails

    Example:
        >>> operation = DataOperation(type="read", path="/data/customers.csv")
        >>> context = ClassificationContext(user=current_user)
        >>> result = classify_data_operation(operation, context)
        >>> print(result.tier)
        DataTier.PROPRIETARY
        >>> print(result.tags)
        ['PII', 'GDPR']
    """
```

## Architecture Decision Records (ADRs)

For significant architectural decisions, create an ADR:

```markdown
# ADR-001: Three-Layer Classification Pipeline

## Status
Accepted

## Context
We need a classification system that is both fast and accurate,
handling 90%+ of operations with <10ms latency while maintaining
high accuracy for complex edge cases.

## Decision
Use a three-layer pipeline:
1. Heuristics layer (regex, path analysis) - <1ms, 90% of operations
2. Embeddings layer (semantic similarity) - <10ms, 8% of operations
3. LLM reasoning layer (context-aware) - <200ms, 2% of operations

## Consequences
- Fast classification for common cases
- Accurate handling of complex scenarios
- Increased system complexity (three layers to maintain)
- Requires embedding model deployment
- LLM costs for 2% of operations

## Alternatives Considered
- Pure LLM classification (rejected: too slow and expensive)
- Pure heuristics (rejected: insufficient accuracy)
- Two-layer system without embeddings (rejected: accuracy gap too large)
```

Store in `docs/adr/`.

## Communication

### GitHub Discussions

Use for:
- Feature proposals
- Design discussions
- Help requests
- Sharing ideas

### GitHub Issues

Use for:
- Bug reports
- Feature requests
- Specific tasks

**Good issue example:**
```markdown
Title: Add Snowflake data sharing governance support

**Description:**
Currently Lacuna tracks lineage within a single system, but doesn't
handle Snowflake data sharing scenarios where data is shared across
different Snowflake accounts.

**Proposed Solution:**
Extend lineage tracking to capture cross-account data sharing:
- Track when data is shared to external accounts
- Maintain classification across account boundaries
- Generate audit trail for shared data access

**Example Use Case:**
```python
# Share data to partner account
share_data(
    data="customer_analytics",
    target_account="partner_account",
    classification=DataTier.INTERNAL,
    allowed_operations=["read"]
)
```

**Impact:**
- Changes to lineage tracking system
- New Snowflake integration module
- Policy engine updates for cross-account rules
- Audit logging for data sharing events
- Tests for cross-account scenarios

**Questions:**
- How to handle classification when external account has different policies?
- Should we require manual approval for PROPRIETARY data sharing?
- How to track data access in external accounts?
```

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist

1. Update CHANGELOG.md
2. Update version in:
   - `setup.py` or `pyproject.toml`
   - `lacuna/__init__.py`
3. Run full test suite: `pytest`
4. Test OPA policies: `opa test policies/`
5. Tag release: `git tag v0.2.0`
6. Push tags: `git push --tags`
7. Create GitHub release with notes
8. Publish to PyPI: `python -m build && twine upload dist/*`
9. Update documentation site (if applicable)

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md
- GitHub contribution graphs
- Release notes
- Project documentation

## Questions?

- Check [GitHub Discussions](https://github.com/witlox/lacuna/discussions)
- Read the [documentation](docs/)
- Join our community channels

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

Thank you for contributing to self-service data governance and compliance!
