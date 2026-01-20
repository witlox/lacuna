# REST API Reference

Lacuna provides a comprehensive REST API for integration with external systems.

## Base URL

```
http://localhost:8000/api/v1
```

All API endpoints are prefixed with `/api/v1`.

## Authentication

Lacuna uses API key authentication for programmatic access:

```bash
# Include API key in Authorization header
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/classify
```

To generate an API key, use the admin dashboard or CLI:

```bash
lacuna admin create-api-key --user analyst@example.com
```

## Endpoints

### Classification

#### Classify Data

Classify a query or data for sensitivity:

```http
POST /api/v1/classify
```

**Request Body:**

```json
{
  "query": "Show me all customer emails and SSNs",
  "context": {
    "user_id": "analyst@example.com",
    "department": "analytics"
  }
}
```

**Response:**

```json
{
  "tier": "PROPRIETARY",
  "confidence": 0.95,
  "tags": ["PII", "GDPR", "SSN"],
  "reasoning": "Contains personally identifiable information (email, SSN)",
  "classifier_used": "heuristic"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all customer emails",
    "context": {"user_id": "analyst@example.com"}
  }'
```

### Governance Evaluation

#### Evaluate Operation

Evaluate whether a data operation is allowed:

```http
POST /api/v1/evaluate
```

**Request Body:**

```json
{
  "operation_type": "EXPORT",
  "source_resources": ["customers.csv"],
  "destination_resource": "/home/user/Downloads/export.csv",
  "user_context": {
    "user_id": "analyst@example.com",
    "role": "data_analyst",
    "department": "analytics"
  }
}
```

**Response:**

```json
{
  "allowed": false,
  "reasoning": "Cannot export PII data to unmanaged location",
  "classification": {
    "tier": "PROPRIETARY",
    "tags": ["PII", "GDPR"]
  },
  "policy_evaluation": {
    "policy_id": "P-2024-001",
    "policy_name": "PII Export Restrictions"
  },
  "alternatives": [
    "Use anonymized version: anonymize(data, ['email', 'ssn'])",
    "Save to governed location: /governed/workspace/",
    "Request exception: https://governance.example.com/exception"
  ]
}
```

### Lineage

#### Get Lineage

Get lineage graph for a resource:

```http
GET /api/v1/lineage/{resource_id}
```

**Parameters:**

- `resource_id` (path) - Resource identifier (e.g., "customer_analysis.csv")
- `depth` (query, optional) - Maximum depth to traverse (default: 10)
- `direction` (query, optional) - "upstream", "downstream", or "both" (default: "both")

**Response:**

```json
{
  "resource_id": "customer_analysis.csv",
  "classification": {
    "tier": "PROPRIETARY",
    "tags": ["PII", "GDPR"]
  },
  "upstream": [
    {
      "resource_id": "customers.csv",
      "classification": {"tier": "PROPRIETARY", "tags": ["PII"]},
      "operation": "READ",
      "timestamp": "2025-01-20T10:30:00Z"
    }
  ],
  "downstream": [],
  "depth": 1
}
```

**Example:**

```bash
curl http://localhost:8000/api/v1/lineage/customer_analysis.csv?depth=5
```

#### Get Upstream Lineage

Get all upstream dependencies:

```http
POST /api/v1/lineage/upstream
```

**Request Body:**

```json
{
  "resource_id": "customer_analysis.csv",
  "max_depth": 10
}
```

#### Get Downstream Impact

Get all downstream dependencies:

```http
POST /api/v1/lineage/downstream
```

**Request Body:**

```json
{
  "resource_id": "customers.csv",
  "max_depth": 10
}
```

### Audit Logs

#### Query Audit Logs

Retrieve audit logs with filters:

```http
POST /api/v1/audit/query
```

**Request Body:**

```json
{
  "user_id": "analyst@example.com",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-31T23:59:59Z",
  "operation_types": ["READ", "EXPORT"],
  "allowed_only": false,
  "limit": 100,
  "offset": 0
}
```

**Response:**

```json
{
  "total": 1247,
  "records": [
    {
      "id": "audit-123",
      "timestamp": "2025-01-20T10:30:00Z",
      "user_id": "analyst@example.com",
      "operation_type": "EXPORT",
      "resource": "customers.csv",
      "allowed": false,
      "classification": {
        "tier": "PROPRIETARY",
        "tags": ["PII"]
      },
      "reasoning": "Cannot export PII to unmanaged location"
    }
  ]
}
```

#### Get Audit Logs

Simple retrieval with pagination:

```http
GET /api/v1/audit/logs
```

**Parameters:**

- `limit` (query, optional) - Records per page (default: 100, max: 1000)
- `offset` (query, optional) - Starting record (default: 0)
- `user_id` (query, optional) - Filter by user

**Example:**

```bash
curl "http://localhost:8000/api/v1/audit/logs?limit=50&user_id=analyst@example.com"
```

### Health Checks

#### Health Check

Basic health check:

```http
GET /api/v1/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "2025.1.42",
  "timestamp": "2025-01-20T10:30:00Z"
}
```

#### Readiness Check

Check if all services are ready:

```http
GET /api/v1/health/ready
```

**Response:**

```json
{
  "ready": true,
  "services": {
    "database": "connected",
    "redis": "connected",
    "opa": "connected"
  }
}
```

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource 'unknown.csv' not found in lineage",
    "details": {
      "resource_id": "unknown.csv"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `CLASSIFICATION_FAILED` | 500 | Classification pipeline error |
| `POLICY_EVALUATION_FAILED` | 500 | Policy engine error |

## Rate Limiting

API requests are rate-limited:

- **Authenticated**: 1000 requests/hour
- **Unauthenticated**: 100 requests/hour

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1642694400
```

## Interactive Documentation

Lacuna provides interactive API documentation via Swagger UI:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Client Libraries

### Python

```python
import requests

class LacunaClient:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def classify(self, query, context=None):
        response = requests.post(
            f"{self.base_url}/api/v1/classify",
            json={"query": query, "context": context},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def evaluate(self, operation):
        response = requests.post(
            f"{self.base_url}/api/v1/evaluate",
            json=operation,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = LacunaClient(api_key="your-api-key")
result = client.classify("Show me customer emails")
print(result["tier"])
```

See [`examples/api_client.py`](https://github.com/witlox/lacuna/blob/main/examples/api_client.py) for a complete example.

### cURL

```bash
#!/bin/bash
API_KEY="your-api-key"
BASE_URL="http://localhost:8000/api/v1"

# Classify
curl -X POST "$BASE_URL/classify" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me customer emails"}'

# Evaluate
curl -X POST "$BASE_URL/evaluate" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "EXPORT",
    "source_resources": ["customers.csv"],
    "user_context": {"user_id": "analyst@example.com"}
  }'
```

## Next Steps

- **[Python SDK Reference](python.md)** - Python API documentation
- **[Integration Guide](../INTEGRATIONS.md)** - Platform integrations
- **[Examples](https://github.com/witlox/lacuna/tree/main/examples)** - Code examples
