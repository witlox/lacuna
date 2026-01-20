# Lacuna

**Protected space for data governance, lineage, and privacy-aware operations**

***
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Build](https://github.com/witlox/lacuna/actions/workflows/build.yml/badge.svg)](https://github.com/witlox/lacuna/actions/workflows/build.yml)
[![Test](https://github.com/witlox/lacuna/actions/workflows/test.yml/badge.svg)](https://github.com/witlox/lacuna/actions/workflows/test.yml)
[![Validate](https://github.com/witlox/lacuna/actions/workflows/validate.yml/badge.svg)](https://github.com/witlox/lacuna/actions/workflows/validate.yml)
[![Package](https://github.com/witlox/lacuna/actions/workflows/package.yml/badge.svg)](https://github.com/witlox/lacuna/actions/workflows/package.yml)
[![codecov](https://codecov.io/gh/witlox/lacuna/branch/main/graph/badge.svg)](https://codecov.io/gh/witlox/lacuna)
***
[![FOSSA Status](https://app.fossa.com/api/projects/custom%2B4756%2Fgithub.com%2Fwitlox%2Flacuna.svg?type=shield&issueType=license)](https://app.fossa.com/projects/custom%2B4756%2Fgithub.com%2Fwitlox%2Flacuna?ref=badge_shield&issueType=license)
[![FOSSA Status](https://app.fossa.com/api/projects/custom%2B4756%2Fgithub.com%2Fwitlox%2Flacuna.svg?type=shield&issueType=security)](https://app.fossa.com/projects/custom%2B4756%2Fgithub.com%2Fwitlox%2Flacuna?ref=badge_shield&issueType=security)
***


## The Problem

Organizations deploying local LLMs and data platforms face a critical challenge: **How do you enable self-service data access while maintaining governance, lineage tracking, and compliance?**

Current solutions require choosing between:
- **Strict centralized control** → Bottlenecks, slow innovation
- **Complete self-service** → Compliance violations, data leaks, audit failures

**Lacuna solves this by creating a "protected space" where:**
- Users see what they're doing in real-time
- Central teams define policies as code
- Systems automatically classify and route data operations
- Complete audit trails satisfy ISO 27001/27002
- Lineage and provenance are captured automatically

## The Solution

Lacuna is a **policy-aware data governance engine** that:

1. **Classifies data operations automatically** using a three-layer pipeline (heuristics → embeddings → LLM)
2. **Enforces policies in real-time** with clear, actionable feedback to users
3. **Tracks complete lineage** across transformations, joins, and exports
4. **Captures comprehensive provenance** (who, what, when, why, how)
5. **Maintains ISO 27001-compliant audit logs** with tamper-evident hash chains
6. **Integrates with existing tools** (dbt, Databricks, Snowflake, OPA)

## Core Use Cases

### Use Case 1: Real-Time Policy Enforcement

**Scenario:** Data analyst attempting to export customer data

```python
# User's notebook
import pandas as pd

customers = pd.read_csv("customers.csv")  
# ✓ Lacuna detects: PII data loaded, context updated

analysis = customers.merge(sales, on="customer_id")
# ✓ Lacuna classifies: PII propagates through join

analysis.to_csv("~/Downloads/export.csv")
# ✗ Lacuna blocks with clear message:
"""
❌ Governance Policy Violation

Action: Export to ~/Downloads/export.csv
Reason: Cannot export PII data to unmanaged location
Classification: PROPRIETARY (inherited from customers.csv)
Tags: PII, GDPR, FINANCIAL

Alternatives:
1. Use anonymized version: analysis_anon = anonymize(analysis, ['customer_id', 'email'])
2. Save to governed location: analysis.to_csv("/governed/workspace/analysis.csv")
3. Request exception: https://governance.example.com/exception

Policy: P-2024-001 (PII Export Restrictions)
Steward: data-governance@example.com
"""
```

### Use Case 2: Automated Lineage Tracking

**Scenario:** Understanding data dependencies

```python
from lacuna import LineageTracker

# Query lineage
lineage = LineageTracker.get_lineage("analysis.csv")

print(lineage.to_graph())
"""
analysis.csv (PROPRIETARY, tags: PII, GDPR, FINANCIAL)
├─ customers.csv (PROPRIETARY, tags: PII, GDPR)
│  └─ raw.customer_master (PROPRIETARY, tags: PII)
│     └─ salesforce.contacts (PROPRIETARY, tags: PII)
└─ sales.csv (INTERNAL, tags: FINANCIAL)
   └─ raw.transactions (INTERNAL, tags: FINANCIAL)
"""

# Check downstream impact
downstream = LineageTracker.get_downstream("customers.csv")
print(f"Changing customers.csv will impact {len(downstream)} artifacts")
```

### Use Case 3: ISO 27001 Audit Compliance

**Scenario:** Annual compliance audit

```python
from lacuna.audit import ComplianceReporter

# Generate ISO 27001 A.9.4 report (Access Control)
report = ComplianceReporter.generate_a_9_4_report(
    start_date="2025-01-01",
    end_date="2025-12-31"
)

# Report includes:
# - All data access attempts (successful and failed)
# - Classification decisions with reasoning
# - Policy violations with user responses
# - Administrative actions
# - Complete audit trail with hash chain verification
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Data Operation                      │
│  (read, write, join, export, transform, query)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Operation Interceptor Layer                    │
│  • File system operations (FUSE)                            │
│  • Database queries (SQLAlchemy middleware)                 │
│  • Notebook operations (IPython magic)                      │
│  • dbt runs (post-hooks)                                    │
│  • API calls (proxy)                                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           Three-Layer Classification Pipeline               │
│                                                             │
│  Layer 1: Heuristics (<1ms)                                 │
│  ├─ Regex patterns for known sensitive terms                │
│  ├─ File path analysis                                      │
│  └─ Handles 90% of operations                               │
│                                                             │
│  Layer 2: Embeddings (<10ms)                                │
│  ├─ Semantic similarity to known examples                   │
│  ├─ Pre-computed embeddings                                 │
│  └─ Handles 8% of operations                                │
│                                                             │
│  Layer 3: LLM Reasoning (<200ms)                            │
│  ├─ Complex context-dependent decisions                     │
│  ├─ Multi-source lineage inference                          │
│  └─ Handles 2% of operations                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Lineage & Provenance Engine                    │
│  • Track source → transformation → destination              │
│  • Classify derived data (inheritance rules)                │
│  • Tag propagation through operations                       │
│  • Business context capture                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            Policy Engine (OPA Integration)                  │
│  • Evaluate operation against policies                      │
│  • Consider: data tier, user role, destination, purpose     │
│  • Return: allow/deny + reasoning + alternatives            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            ISO 27001 Audit Logging                          │
│  • Tamper-evident hash chain                                │
│  • Complete provenance (who, what, when, why, how)          │
│  • PostgreSQL append-only storage                           │
│  • Real-time alerting for violations                        │
│  • Compliance report generation                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              User Feedback Interface                        │
│  • Inline notebook warnings                                 │
│  • IDE integration (VS Code, PyCharm)                       │
│  • CLI pre-execution checks                                 │
│  • Web dashboard for compliance status                      │
└─────────────────────────────────────────────────────────────┘
```

## Sensitivity Tiers

Lacuna classifies all data into three tiers:

### PROPRIETARY
- **Definition**: Data that would provide competitive advantage or violate confidentiality if disclosed
- **Examples**: Customer PII, proprietary algorithms, internal pricing, strategic plans
- **Routing**: Local only, requires approval for export
- **Retention**: 7+ years for compliance

### INTERNAL
- **Definition**: Data that should remain within organization but isn't competitively sensitive
- **Examples**: Internal tooling, team processes, general analytics
- **Routing**: Internal systems, no external sharing
- **Retention**: 1-3 years

### PUBLIC
- **Definition**: Information that is or could be publicly available
- **Examples**: Public documentation, open-source code, published research
- **Routing**: No restrictions
- **Retention**: 1 year minimum

**Key principle**: Classification propagates through lineage. Joining PUBLIC + PROPRIETARY = PROPRIETARY.

## Key Features

### Governance & Classification
- **Automatic data classification** using three-layer pipeline (heuristics, embeddings, LLM)
- **Context-aware decisions** considering conversation, files, lineage
- **Policy-as-code** using Open Policy Agent (OPA)
- **User override** with feedback loop for continuous improvement

### Lineage & Provenance
- **Automatic lineage tracking** across file operations, SQL queries, transformations
- **Classification inheritance** through joins, aggregations, derivations
- **Tag propagation** (PII, PHI, FINANCIAL) through data flows
- **Business context capture** (purpose, justification, approvals)

### Audit & Compliance
- **ISO 27001-compliant logging** with tamper-evident hash chains
- **Complete provenance** (who, what, when, why, how)
- **Real-time alerting** for policy violations and security events
- **Compliance reports** (A.9.4, A.12.4, GDPR, HIPAA)
- **7-year retention** with automated archival to cold storage

### Integration & Extensibility
- **Pluggable architecture** for custom classifiers and policies
- **Native integrations**: dbt, Databricks Unity Catalog, Snowflake, OPA
- **Developer tools**: Jupyter magic, VS Code extension, CLI
- **REST API** for custom integrations

### Performance
- **<10ms classification** for 98% of operations (heuristics + embeddings)
- **Caching layer** for repeated patterns
- **Asynchronous audit logging** (non-blocking)
- **Batch processing** for bulk operations

## Quick Start

### Development Mode

The fastest way to try Lacuna locally:

```bash
# Clone and install
git clone https://github.com/witlox/lacuna.git
cd lacuna
pip install -e .

# Start in dev mode (uses SQLite, no external dependencies)
lacuna dev

# Open in browser
# API Docs: http://127.0.0.1:8000/docs
# User Dashboard: http://127.0.0.1:8000/user/dashboard
# Admin Dashboard: http://127.0.0.1:8000/admin/
```

Dev mode uses lightweight backends (SQLite, in-memory cache) so you can explore Lacuna without setting up PostgreSQL, Redis, or OPA.

### Production Mode

For production deployments with full features:

```bash
# Using Docker
docker pull ghcr.io/witlox/lacuna:latest
docker run -d -p 8000:8000 ghcr.io/witlox/lacuna:latest

# Or install via pip
pip install lacuna
lacuna serve --host 0.0.0.0 --port 8000
```

See [Deployment Guide](docs/DEPLOYMENT.md) for details, or use the production-ready configurations:

```bash
# Docker Compose production stack
docker compose -f deploy/docker/docker-compose.prod.yaml up -d

# High-availability with PostgreSQL replication
docker compose -f deploy/docker/docker-compose.ha.yaml up -d

# Kubernetes with Helm
helm install lacuna ./deploy/helm/lacuna -f deploy/helm/lacuna/values-production.yaml
```

## Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Using the web UI and CLI
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and data flow
- **[Development Guide](docs/DEVELOPMENT.md)** - Local setup and dev mode
- **[Data Governance Guide](docs/DATA_GOVERNANCE.md)** - Self-service governance model
- **[Lineage & Provenance](docs/LINEAGE.md)** - Tracking data flows
- **[ISO 27001 Audit Logging](docs/AUDIT_LOGGING.md)** - Compliance implementation
- **[Policy-as-Code](docs/POLICY_AS_CODE.md)** - Writing OPA policies
- **[Integration Guide](docs/INTEGRATIONS.md)** - dbt, Databricks, Snowflake
- **[Plugin Development](docs/PLUGINS.md)** - Extending Lacuna
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production setup and authentication

## Examples

The [`examples/`](examples/) directory contains runnable scripts demonstrating Lacuna features:

| Example | Description |
|---------|-------------|
| [`basic_classification.py`](examples/basic_classification.py) | Classify data and check sensitivity tiers |
| [`policy_evaluation.py`](examples/policy_evaluation.py) | Evaluate operations against policies |
| [`lineage_tracking.py`](examples/lineage_tracking.py) | Track data lineage and provenance |
| [`audit_logging.py`](examples/audit_logging.py) | Query and inspect audit logs |
| [`api_client.py`](examples/api_client.py) | HTTP client for the REST API |
| [`batch_classification.py`](examples/batch_classification.py) | Classify multiple items efficiently |
| [`custom_classifier.py`](examples/custom_classifier.py) | Create custom classification rules |
| [`governance_workflow.py`](examples/governance_workflow.py) | Complete governance workflow |

```bash
# Run examples after starting dev server
lacuna dev &
python examples/basic_classification.py
```

## Why Lacuna?

### The Name

**Lacuna** (Latin): A gap, cavity, or protected space

In anatomy, a lacuna is a small cavity in bone or cartilage that protects cells. In manuscripts, a lacuna is a missing section that reveals what's intentionally kept private.

**In data governance**, Lacuna creates the protected space where:
- Sensitive data stays secure (within the cavity)
- Appropriate data flows freely (through the controlled gap)
- The boundary is enforced automatically (by classification and policy)

### The Market Gap

Existing solutions address either:
1. **Data catalogs** (Alation, Collibra) - Passive metadata, no real-time enforcement
2. **Access control** (Databricks, Snowflake) - Permission gates, but no operation-level governance
3. **DLP tools** (Microsoft Purview) - Detection only, limited lineage
4. **Policy engines** (OPA) - Enforcement infrastructure, but no data-aware classification

**Lacuna uniquely combines:**
- Real-time operation interception
- Automatic data classification with lineage
- Policy enforcement with user feedback
- ISO 27001-compliant audit logging
- Self-service model with central governance

### Who This Is For

**Target Organizations:**
- Enterprises with data governance requirements
- Regulated industries (finance, healthcare, government)
- Companies with proprietary data assets
- Organizations deploying local data platforms
- Teams needing self-service with compliance

**Target Users:**
- Data analysts (need self-service access)
- Data engineers (building pipelines)
- Data governance teams (defining policies)
- Compliance officers (generating audit reports)
- Security teams (monitoring access)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to set up development environment
- Code style guidelines
- Testing requirements
- Plugin development guide
- Documentation standards

## License

Lacuna is licensed under the [Apache 2.0](LICENSE).

## Support

- **Issues**: https://github.com/witlox/lacuna/issues
- **Discussions**: https://github.com/witlox/lacuna/discussions

## Citation

If you use Lacuna in academic research, please cite:

```bibtex
@software{lacuna2025,
  title = {Lacuna: Self-Service Data Governance with Real-Time Policy Enforcement},
  author = {Lacuna Contributors},
  year = {2025},
  url = {https://github.com/witlox/lacuna}
}
```
