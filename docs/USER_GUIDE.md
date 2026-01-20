# User Guide

**Lacuna** provides both a web interface and command-line interface for data governance operations.

---

## Web Interface

### User Dashboard

Access at: `http://localhost:8000/user/dashboard`

The user dashboard provides a personal view of your data governance activity:

#### Dashboard Overview
- **Recent Activity**: Your latest classifications and policy evaluations
- **Violation Summary**: Count of policy violations in the last 30 days
- **Quick Stats**: Total queries, approval rate, common data tiers

#### History (`/user/history`)
View your complete activity history with filters:
- **Date Range**: Filter by time period
- **Action Type**: Classification, evaluation, export
- **Result**: Allowed, denied, blocked

Example use cases:
- Review what data you accessed last week
- Find a specific query you ran previously
- Export your activity for compliance reporting

#### Violations (`/user/violations`)
Review policy violations and understand what went wrong:
- **Violation Details**: What rule was triggered
- **Context**: The data and operation involved
- **Recommendations**: How to avoid similar violations

#### Recommendations (`/user/recommendations`)
Personalized suggestions based on your activity patterns:
- Common mistakes and how to fix them
- Best practices for data handling
- Training resources for specific data types

---

### Admin Dashboard

Access at: `http://localhost:8000/admin/` (requires admin privileges)

#### Dashboard (`/admin/`)
System-wide overview:
- **Total Events**: Classification and evaluation counts
- **Violations Today**: Policy denials requiring attention
- **System Health**: Backend service status
- **Top Violators**: Users with most policy violations

#### Users (`/admin/users`)
User management and activity monitoring:
- View all users who have interacted with the system
- See per-user violation counts
- Filter by activity level or department

#### Audit (`/admin/audit`)
Complete audit log with advanced filtering:
- **User ID**: Filter by specific user
- **Resource**: Filter by data asset
- **Event Type**: Classification, evaluation, export, etc.
- **Result**: Allowed, denied, blocked
- **Date Range**: Custom time windows

Export audit logs for compliance reporting.

#### Policies (`/admin/policies`)
Policy management:
- View active policies
- See policy evaluation statistics
- Check policy version history

#### Config (`/admin/config`)
System configuration:
- **Proprietary Terms**: Keywords that trigger PROPRIETARY classification
- **Project Mappings**: Project-to-classification mappings
- **Customer Terms**: Customer-specific sensitive terms
- **System Settings**: Classification thresholds, cache TTL, etc.

#### API Keys (`/admin/api-keys`)
Service account management:
- **Create Keys**: Generate API keys for automation (dbt, CI/CD, etc.)
- **View Keys**: See all keys with usage statistics
- **Revoke/Delete**: Disable compromised or unused keys

Creating an API key:
1. Click "Generate API Key"
2. Enter a name (e.g., "dbt-production")
3. Set the service account ID (username for audit logs)
4. Optionally add groups and expiration
5. **Copy the key immediately** - it won't be shown again!

#### Alerts (`/admin/alerts`)
Alert configuration and history:
- View triggered alerts
- Configure alert thresholds
- Set up notification channels

---

## Command-Line Interface

### Getting Started

```bash
# Install Lacuna
pip install lacuna

# Verify installation
lacuna --version

# Get help
lacuna --help
```

### Development Mode

```bash
# Start dev server (no external dependencies needed)
lacuna dev

# Custom port
lacuna dev --port 8080

# Disable auto-reload
lacuna dev --no-reload
```

Dev mode uses:
- SQLite instead of PostgreSQL
- In-memory cache instead of Redis
- Heuristic classifier only (no LLM/embeddings)
- Authentication bypassed (admin user)

### Classification

```bash
# Classify a query
lacuna classify "SELECT * FROM customers WHERE email LIKE '%@gmail.com'"

# Classify with context
lacuna classify "SELECT revenue FROM sales" --project finance --user analyst@company.com

# Batch classification from file
lacuna classify --file queries.txt --output results.json

# Output formats
lacuna classify "query" --format json
lacuna classify "query" --format table
lacuna classify "query" --format yaml
```

### Policy Evaluation

```bash
# Evaluate an operation
lacuna evaluate \
  --operation read \
  --resource customers \
  --user analyst@company.com

# Evaluate an export
lacuna evaluate \
  --operation export \
  --resource customers \
  --destination /tmp/export.csv \
  --user analyst@company.com

# With purpose justification
lacuna evaluate \
  --operation export \
  --resource financial_data \
  --destination s3://bucket/path \
  --purpose "Q4 reporting" \
  --user analyst@company.com
```

### Lineage

```bash
# Get lineage for an artifact
lacuna lineage get customers_table

# Show upstream dependencies
lacuna lineage upstream customers_table

# Show downstream dependents  
lacuna lineage downstream customers_table

# Impact analysis (what would be affected by changes)
lacuna lineage impact customers_table
```

### Audit

```bash
# Query audit logs
lacuna audit query --limit 100

# Filter by user
lacuna audit query --user analyst@company.com

# Filter by result
lacuna audit query --result denied --limit 50

# Filter by date range
lacuna audit query --start 2024-01-01 --end 2024-01-31

# Export audit logs
lacuna audit export --format csv --output audit_jan.csv

# Verify audit log integrity
lacuna audit verify --start 2024-01-01
```

### Admin Commands

Admin commands require appropriate permissions.

#### Configuration Management

```bash
# Show current config
lacuna admin config show

# Validate config
lacuna admin config validate

# Reload config (hot reload)
lacuna admin config reload
```

#### Proprietary Terms

```bash
# List proprietary terms
lacuna admin terms list

# Add a term
lacuna admin terms add "Project Phoenix"

# Remove a term
lacuna admin terms remove "Old Project"

# Bulk import from file
lacuna admin terms import terms.txt
```

#### Project Mappings

```bash
# List project mappings
lacuna admin projects list

# Add a project with classification
lacuna admin projects add "secret-project" --tier PROPRIETARY

# Remove a project
lacuna admin projects remove "old-project"
```

#### Customer Terms

```bash
# List customer terms
lacuna admin customers list

# Add customer-specific terms
lacuna admin customers add "Acme Corp" --terms "acme,acme-corp,acmecorp"

# Remove customer
lacuna admin customers remove "Old Customer"
```

#### Policy Management

```bash
# List policies
lacuna admin policy list

# Show policy details
lacuna admin policy show export-policy

# Validate policy syntax
lacuna admin policy validate policies/new-policy.rego

# Deploy a policy
lacuna admin policy deploy policies/new-policy.rego
```

#### User Management

```bash
# List users
lacuna admin users list

# Show user details
lacuna admin users show analyst@company.com

# View user violations
lacuna admin users violations analyst@company.com
```

#### API Key Management

```bash
# List API keys
lacuna admin apikey list

# Create a new API key
lacuna admin apikey create \
  --name "dbt-production" \
  --service-account "svc-dbt" \
  --groups "data-engineers"

# Revoke a key
lacuna admin apikey revoke KEY_ID

# Delete a key
lacuna admin apikey delete KEY_ID
```

### Server Management

```bash
# Start production server
lacuna server --host 0.0.0.0 --port 8000

# With workers
lacuna server --workers 4

# With SSL
lacuna server --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Configuration

```bash
# Show effective configuration
lacuna config show

# Validate configuration
lacuna config validate

# Show config file location
lacuna config path
```

---

## API Usage

### Authentication

For production, include authentication headers:

```bash
# With API key
curl -H "Authorization: Bearer lac_your_key_here" \
  http://localhost:8000/api/v1/classify

# Behind reverse proxy (headers set by proxy)
# X-User, X-Email, X-Groups headers are used
```

### Classification API

```bash
# Classify a query
curl -X POST http://localhost:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT email, ssn FROM users",
    "project": "analytics",
    "user_id": "analyst@company.com"
  }'

# Response
{
  "tier": "PROPRIETARY",
  "confidence": 0.95,
  "reasoning": "Contains PII (SSN pattern detected)",
  "tags": ["PII", "SSN"],
  "classifier": "heuristic",
  "latency_ms": 2.5
}
```

### Evaluation API

```bash
# Evaluate an operation
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "export",
    "resource_type": "table",
    "resource_id": "customers",
    "destination": "/tmp/export.csv"
  }'

# Response
{
  "allowed": false,
  "classification_tier": "PROPRIETARY",
  "reasoning": "Export of PROPRIETARY data to unencrypted destination denied",
  "alternatives": [
    "Export to encrypted S3 bucket",
    "Request data access approval",
    "Use anonymized view instead"
  ],
  "evaluation_id": "eval-123"
}
```

### OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Common Workflows

### Setting Up a New Project

1. Add project to configuration:
   ```bash
   lacuna admin projects add "new-project" --tier INTERNAL
   ```

2. Add project-specific terms:
   ```bash
   lacuna admin terms add "new-project-secret"
   ```

3. Verify classification:
   ```bash
   lacuna classify "SELECT * FROM new_project_data"
   ```

### Investigating a Violation

1. Find the violation in audit logs:
   ```bash
   lacuna audit query --user violator@company.com --result denied
   ```

2. Get details:
   ```bash
   lacuna audit show EVENT_ID
   ```

3. Check user's violation history:
   ```bash
   lacuna admin users violations violator@company.com
   ```

### Setting Up Service Account Access

1. Create API key:
   ```bash
   lacuna admin apikey create \
     --name "dbt-production" \
     --service-account "svc-dbt" \
     --groups "data-engineers" \
     --expires-days 90
   ```

2. Store the key securely (shown only once)

3. Use in automation:
   ```bash
   export LACUNA_API_KEY="lac_xxx..."
   curl -H "Authorization: Bearer $LACUNA_API_KEY" \
     http://lacuna.internal/api/v1/classify
   ```

---

## Troubleshooting

### Dev Mode Issues

```bash
# Check if port is in use
lsof -i :8000

# Clear dev database
rm -rf data/lacuna_dev.db

# Restart with verbose logging
LACUNA_LOG_LEVEL=DEBUG lacuna dev
```

### Authentication Issues

```bash
# Check if running in dev mode (auth bypassed)
lacuna config show | grep dev_mode

# Verify API key is valid
curl -v -H "Authorization: Bearer lac_xxx" \
  http://localhost:8000/api/v1/health
```

### Classification Not Working

```bash
# Check classifier configuration
lacuna config show | grep classifier

# Test with known PII
lacuna classify "email: test@example.com, SSN: 123-45-6789"

# Check if proprietary terms are loaded
lacuna admin terms list
```

---

For more information:
- [Development Guide](DEVELOPMENT.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Architecture](ARCHITECTURE.md)
