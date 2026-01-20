# Development Guide

**Lacuna** - Local development setup and dev mode

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/witlox/lacuna.git
cd lacuna

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Start in dev mode
lacuna dev
```

That's it! Lacuna is now running at http://127.0.0.1:8000 with:
- API Documentation: http://127.0.0.1:8000/docs
- User Dashboard: http://127.0.0.1:8000/user/dashboard
- Admin Dashboard: http://127.0.0.1:8000/admin/

---

## Development Mode

Dev mode (`lacuna dev`) uses lightweight backends so you can run Lacuna locally without external dependencies:

| Service | Production | Dev Mode |
|---------|-----------|----------|
| **Database** | PostgreSQL | SQLite (`data/lacuna_dev.db`) |
| **Cache** | Redis | In-memory (disabled) |
| **Policy Engine** | OPA | Disabled |
| **Embedding Models** | GPU/CPU intensive | Disabled |
| **LLM Classification** | OpenAI/local LLM | Disabled |
| **Monitoring** | Prometheus/Loki | Disabled |

### Dev Mode Command

```bash
# Start with defaults
lacuna dev

# Custom port
lacuna dev --port 8080

# Disable auto-reload
lacuna dev --no-reload
```

### Environment Variables

Dev mode automatically sets these environment variables:

```bash
LACUNA_ENVIRONMENT=development
LACUNA_DEBUG=true
LACUNA_DATABASE__URL=sqlite:///data/lacuna_dev.db
LACUNA_REDIS__ENABLED=false
LACUNA_CLASSIFICATION__EMBEDDING_ENABLED=false
LACUNA_CLASSIFICATION__LLM_ENABLED=false
LACUNA_POLICY__ENABLED=false
LACUNA_MONITORING__ENABLED=false
LACUNA_LOG_FORMAT=text
LACUNA_LOG_LEVEL=DEBUG
```

### .env.dev Template

Copy `.env.dev` to `.env` for custom configuration:

```bash
cp .env.dev .env
# Edit .env with your settings
```

---

## Project Structure

```
lacuna/
├── lacuna/                 # Main package
│   ├── api/                # FastAPI application
│   │   └── app.py          # Main app with routes
│   ├── audit/              # ISO 27001 audit logging
│   │   ├── backend.py      # PostgreSQL backend
│   │   ├── memory_backend.py  # In-memory (dev mode)
│   │   └── logger.py       # Audit logger
│   ├── classifier/         # Three-layer classification
│   │   ├── heuristic.py    # Fast regex patterns
│   │   ├── embedding.py    # Semantic similarity
│   │   ├── llm.py          # LLM reasoning
│   │   └── pipeline.py     # Classification orchestrator
│   ├── cli/                # Command-line interface
│   │   ├── __init__.py     # Main CLI commands
│   │   └── admin.py        # Admin CLI commands
│   ├── config/             # Configuration management
│   │   ├── loader.py       # YAML config loader
│   │   └── settings.py     # Pydantic settings
│   ├── db/                 # Database layer
│   │   ├── base.py         # SQLAlchemy setup
│   │   └── models.py       # ORM models
│   ├── engine/             # Governance engine
│   │   └── governance.py   # Main engine
│   ├── lineage/            # Data lineage tracking
│   │   ├── backend.py      # PostgreSQL backend
│   │   ├── memory_backend.py  # In-memory (dev mode)
│   │   └── tracker.py      # Lineage tracker
│   ├── models/             # Pydantic models
│   │   ├── audit.py        # Audit records
│   │   ├── classification.py  # Classification types
│   │   ├── data_operation.py  # Operations
│   │   ├── lineage.py      # Lineage graph
│   │   └── policy.py       # Policy decisions
│   ├── policy/             # Policy engine
│   │   ├── client.py       # OPA client
│   │   └── engine.py       # Policy evaluation
│   └── web/                # Web UI
│       ├── routes/         # FastAPI routes
│       │   ├── admin.py    # Admin dashboard
│       │   └── user.py     # User dashboard
│       └── templates/      # Jinja2 templates
│           ├── admin/      # Admin pages
│           └── user/       # User pages
├── config/                 # Configuration files
│   ├── default.yaml        # Default settings
│   └── dev.yaml            # Dev mode settings
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation
├── examples/               # Usage examples
├── migrations/             # Alembic migrations
└── policies/               # OPA policy files
```

---

## Running Tests

```bash
# All tests
make test

# Unit tests only
pytest tests/unit/ -v

# With coverage
pytest --cov=lacuna --cov-report=html

# Integration tests (requires services)
LACUNA_RUN_INTEGRATION_TESTS=true pytest tests/integration/
```

---

## Examples

The [`examples/`](../examples/) directory contains runnable scripts demonstrating Lacuna features:

```bash
# Start dev server in background
lacuna dev &

# Run classification example
python examples/basic_classification.py

# Run full governance workflow
python examples/governance_workflow.py
```

| Example | Description |
|---------|-------------|
| `basic_classification.py` | Classify data sensitivity |
| `policy_evaluation.py` | Evaluate operations against policies |
| `lineage_tracking.py` | Track data lineage |
| `audit_logging.py` | Query audit logs |
| `api_client.py` | REST API HTTP client |
| `batch_classification.py` | Batch classification |
| `custom_classifier.py` | Custom classifiers |
| `governance_workflow.py` | End-to-end workflow |

---

## Code Quality

```bash
# Format code
make format

# Lint
make lint

# Type check
make mypy

# Security scan
make security

# All checks
make validate
```

Individual tools:

```bash
# Ruff (linting + formatting)
ruff check lacuna/ --fix
ruff format lacuna/

# MyPy (type checking)
mypy lacuna/

# Bandit (security)
bandit -r lacuna/
```

---

## Building

```bash
# Build package
make build

# Build Docker image
make docker-build
```

---

## CLI Commands

### Core Commands

```bash
lacuna dev              # Start in development mode
lacuna serve            # Start in production mode
lacuna migrate          # Run database migrations
lacuna config validate  # Validate configuration
lacuna version          # Show version
```

### Admin Commands

```bash
lacuna admin config show           # Show configuration
lacuna admin config set KEY VALUE  # Set config value
lacuna admin users list            # List users
lacuna admin users create          # Create user
lacuna admin policy reload         # Reload policies
lacuna admin terms add PROJECT     # Add proprietary term
```

---

## API Endpoints

When running (`lacuna dev` or `lacuna serve`):

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /health` | Detailed health status |
| `GET /docs` | OpenAPI documentation (Swagger) |
| `GET /redoc` | Alternative API docs (ReDoc) |
| `POST /classify` | Classify a data operation |
| `GET /lineage/{id}` | Get lineage for artifact |
| `GET /audit/records` | Query audit records |

### Web Dashboards

| URL | Description |
|-----|-------------|
| `/user/dashboard` | User dashboard |
| `/user/history` | Operation history |
| `/user/violations` | Policy violations |
| `/user/recommendations` | Improvement suggestions |
| `/admin/` | Admin dashboard |
| `/admin/users` | User management |
| `/admin/audit` | Audit log viewer |
| `/admin/policies` | Policy management |
| `/admin/config` | System configuration |
| `/admin/alerts` | Alert management |

---

## Configuration

### Configuration Files

Lacuna loads configuration in order (later overrides earlier):

1. `config/default.yaml` - Default settings
2. `config/{environment}.yaml` - Environment-specific (e.g., `dev.yaml`)
3. Environment variables (`LACUNA_*`)
4. `.env` file (if present)

### Key Settings

```yaml
# config/dev.yaml
environment: development
debug: true

database:
  url: "sqlite:///data/lacuna_dev.db"

redis:
  enabled: false

classification:
  embedding:
    enabled: false
  llm:
    enabled: false

policy:
  enabled: false

monitoring:
  enabled: false

logging:
  level: DEBUG
  format: text
```

### Environment Variable Mapping

Environment variables use `__` for nested keys:

```bash
LACUNA_DATABASE__URL=postgresql://...
LACUNA_REDIS__ENABLED=true
LACUNA_CLASSIFICATION__LLM__MODEL=gpt-4
```

---

## Database Migrations

```bash
# Generate migration after model changes
lacuna migrate --generate --message "Add new field"

# Run pending migrations
lacuna migrate

# Rollback one revision
lacuna migrate --revision -1
```

---

## Debugging

### Enable Debug Mode

```bash
export LACUNA_DEBUG=true
export LACUNA_LOG_LEVEL=DEBUG
lacuna dev
```

### View Logs

Dev mode uses human-readable text logs. For JSON logs:

```bash
export LACUNA_LOG_FORMAT=json
```

### Database Inspection

```bash
# SQLite (dev mode)
sqlite3 data/lacuna_dev.db ".tables"
sqlite3 data/lacuna_dev.db "SELECT * FROM audit_records LIMIT 5;"

# PostgreSQL (production)
psql $LACUNA_DATABASE__URL -c "SELECT * FROM audit_records LIMIT 5;"
```

---

## Extending Lacuna

### Custom Classifier

```python
from lacuna.classifier.base import BaseClassifier
from lacuna.models.classification import Classification

class MyClassifier(BaseClassifier):
    def classify(self, content: str, context: dict) -> Classification:
        # Your classification logic
        return Classification(tier="INTERNAL", confidence=0.9)
```

### Custom Policy

Create a Rego policy in `policies/`:

```rego
# policies/custom.rego
package lacuna.custom

deny[msg] {
    input.operation.type == "export"
    input.classification.tier == "PROPRIETARY"
    not input.user.roles[_] == "data_steward"
    msg := "Only data stewards can export proprietary data"
}
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Use different port
lacuna dev --port 8080
```

### Database Locked (SQLite)

SQLite can only handle one writer at a time. If you see "database is locked":

```bash
# Remove dev database
rm data/lacuna_dev.db

# Restart
lacuna dev
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e ".[dev]"
```

### Missing Dependencies

```bash
# Install all optional dependencies
pip install -e ".[all]"
```

---

## IDE Setup

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)

`.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.formatting.provider": "none",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true
}
```

### PyCharm

1. Set Python interpreter to `.venv/bin/python`
2. Enable Ruff plugin
3. Enable MyPy plugin
4. Mark `lacuna/` as Sources Root

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Code style guidelines
- Pull request process
- Testing requirements
- Documentation standards

---

*Happy hacking! 🚀*
