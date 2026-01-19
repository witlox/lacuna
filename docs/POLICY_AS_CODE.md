# Policy as Code with Open Policy Agent

**Lacuna** - The protected space where your knowledge stays yours

Define classification rules as code using Open Policy Agent (OPA) for governance-driven query routing.

---

## Overview

**Policy-as-Code** separates classification rules (owned by compliance/security) from implementation (owned by engineering).

### Why Policy-as-Code?

**Traditional approach** (hardcoded rules):
```python
# Engineering owns both policy AND implementation
if "patient" in query or "PHI" in query:
    return Classification.PROPRIETARY
```

**Problems**:
- Compliance team can't modify rules without engineering
- No audit trail of policy changes
- Rules scattered across codebase
- Can't test policies independently

**Policy-as-Code approach**:
```rego
# Compliance team owns policy (security.rego)
package lacuna.classification

proprietary[reason] {
    contains(lower(input.query), "patient")
    reason := "Query contains PHI indicator"
}
```

**Benefits**:
- ✅ Compliance team controls rules
- ✅ Version-controlled policies (Git)
- ✅ Policy testing framework
- ✅ Audit trail via Git history
- ✅ Centralized governance

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Lacuna Classifier                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Query → Heuristics → Embeddings → OPA → LLM → Result    │
│              ↓            ↓         ↓     ↓              │
│          Fast path    Semantic   Policy  Fallback        │
│           (1ms)       (10ms)    (5ms)   (200ms)          │
│                                   ↓                      │
│                         ┌─────────────────┐              │
│                         │   OPA Server    │              │
│                         │  (Port 8181)    │              │
│                         ├─────────────────┤              │
│                         │ policies/       │              │
│                         │  ├─ base.rego   │              │
│                         │  ├─ healthcare  │              │
│                         │  ├─ finance     │              │
│                         │  └─ custom      │              │
│                         └─────────────────┘              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Installation

**1. Install OPA**

```bash
# Using Docker (recommended)
docker run -p 8181:8181 \
  -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest \
  run --server --addr :8181 /policies

# Or install binary
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa
./opa run --server --addr :8181 policies/
```

**2. Configure Lacuna**

```yaml
# config/plugins.yaml
plugins:
  opa:
    enabled: true
    priority: 10  # High priority (policy enforcement)
    endpoint: "http://localhost:8181"
    policy_path: "lacuna/classification"
    timeout: 1.0  # seconds
    fallback_on_error: true
```

**3. Write first policy**

```rego
# policies/base.rego
package lacuna.classification

import future.keywords.if
import future.keywords.in

# Classification result structure
classification[result] {
    result := {
        "tier": tier,
        "confidence": confidence,
        "reasoning": reasoning
    }
    tier := proprietary_tier
    confidence := 1.0
    reasoning := proprietary_reason
}

classification[result] {
    result := {
        "tier": tier,
        "confidence": confidence,
        "reasoning": reasoning
    }
    tier := "INTERNAL"
    confidence := 0.9
    reasoning := internal_reason
}

classification[result] {
    result := {
        "tier": "PUBLIC",
        "confidence": 0.8,
        "reasoning": "No sensitive patterns detected"
    }
    not proprietary_tier
    not internal_reason
}

# Proprietary rules
proprietary_tier := "PROPRIETARY"
proprietary_reason := reason {
    # Check for project names
    project := input.context.project
    project != "learning"
    reason := sprintf("Project context indicates proprietary: %s", [project])
}

proprietary_reason := reason {
    # Check for customer references
    contains(lower(input.query), "customer")
    reason := "Query references customers"
}

# Internal rules  
internal_reason := "Query about internal processes" {
    process_terms := ["deployment", "infrastructure", "monitoring"]
    some term in process_terms
    contains(lower(input.query), term)
}

# Helper functions
lower(s) := lower {
    lower := lower(s)
}
```

### Testing Policies

```bash
# Test policy locally
opa test policies/ -v

# Test specific scenario
echo '{
  "query": "How do we deploy to customer_acme?",
  "context": {
    "project": "production"
  }
}' | opa eval --data policies/ \
  --input - \
  'data.lacuna.classification.classification'
```

---

## Policy Structure

### Input Schema

OPA receives query context from Lacuna:

```json
{
  "query": "How do we optimize authentication?",
  "context": {
    "project": "project_apollo",
    "conversation": [
      {"role": "user", "content": "Tell me about our auth"},
      {"role": "assistant", "content": "Our auth uses..."}
    ],
    "files": ["auth.py", "config.yaml"],
    "user_id": "user-123",
    "session_id": "session-456",
    "timestamp": "2026-01-19T10:30:00Z"
  }
}
```

### Output Schema

OPA returns classification decision:

```json
{
  "tier": "PROPRIETARY",
  "confidence": 0.95,
  "reasoning": "Matched project name 'project_apollo'",
  "metadata": {
    "matched_rules": ["project_context", "proprietary_term"],
    "policy_version": "1.2.0"
  }
}
```

---

## Policy Examples

### Healthcare (HIPAA)

```rego
# policies/healthcare.rego
package lacuna.classification

import future.keywords.if

# PHI indicators
phi_terms := [
    "patient",
    "diagnosis",
    "treatment",
    "medical record",
    "health information",
    "prescription",
    "ssn",
    "date of birth"
]

# PROPRIETARY: Contains PHI
proprietary_tier := "PROPRIETARY" {
    some term in phi_terms
    contains(lower(input.query), term)
}

proprietary_reason := reason {
    matched_terms := [term | 
        some term in phi_terms
        contains(lower(input.query), term)
    ]
    count(matched_terms) > 0
    reason := sprintf("Query contains PHI indicators: %v", [matched_terms])
}

# PROPRIETARY: Patient ID patterns
proprietary_tier := "PROPRIETARY" {
    regex.match(`\bMRN[-\s]?\d{6,}`, input.query)
}

proprietary_reason := "Query contains medical record number pattern" {
    regex.match(`\bMRN[-\s]?\d{6,}`, input.query)
}

# INTERNAL: Clinical workflows (no patient data)
internal_tier := "INTERNAL" {
    workflow_terms := ["protocol", "procedure", "guideline", "workflow"]
    some term in workflow_terms
    contains(lower(input.query), term)
    not proprietary_tier
}
```

### Finance (PCI-DSS, SOX)

```rego
# policies/finance.rego
package lacuna.classification

import future.keywords.if

# PCI-DSS: Payment card data
proprietary_tier := "PROPRIETARY" {
    pci_terms := [
        "credit card",
        "card number",
        "cvv",
        "cardholder",
        "payment",
        "transaction"
    ]
    some term in pci_terms
    contains(lower(input.query), term)
}

# Credit card number pattern
proprietary_tier := "PROPRIETARY" {
    regex.match(`\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b`, input.query)
}

# SOX: Financial reporting
proprietary_tier := "PROPRIETARY" {
    sox_terms := [
        "earnings",
        "revenue",
        "quarterly results",
        "financial statement",
        "audit"
    ]
    some term in sox_terms
    contains(lower(input.query), term)
    # Additional context check
    input.context.project in ["finance", "accounting"]
}

proprietary_reason := reason {
    matched := [term | 
        term := ["earnings", "revenue", "quarterly results"][_]
        contains(lower(input.query), term)
    ]
    count(matched) > 0
    reason := sprintf("Query contains SOX-sensitive terms: %v", [matched])
}
```

### Defense (ITAR/CUI)

```rego
# policies/defense.rego
package lacuna.classification

import future.keywords.if

# ITAR controlled information
proprietary_tier := "PROPRIETARY" {
    itar_terms := [
        "export control",
        "itar",
        "munitions",
        "defense article",
        "technical data",
        "classified"
    ]
    some term in itar_terms
    contains(lower(input.query), term)
}

# CUI (Controlled Unclassified Information)
proprietary_tier := "PROPRIETARY" {
    cui_markers := [
        "cui",
        "controlled unclassified",
        "fouo",  # For Official Use Only
        "noforn"  # No Foreign Nationals
    ]
    some marker in cui_markers
    contains(lower(input.query), marker)
}

# Security classification levels
proprietary_tier := "PROPRIETARY" {
    classification_levels := [
        "confidential",
        "secret",
        "top secret"
    ]
    some level in classification_levels
    contains(lower(input.query), level)
}

proprietary_reason := "Query contains ITAR/CUI indicators" {
    proprietary_tier == "PROPRIETARY"
}
```

### Custom Organization Rules

```rego
# policies/custom/acme_corp.rego
package lacuna.classification

import future.keywords.if

# Company-specific projects
proprietary_projects := [
    "project_apollo",
    "project_artemis",
    "skunkworks"
]

proprietary_tier := "PROPRIETARY" {
    input.context.project in proprietary_projects
}

# Company-specific customers
proprietary_customers := [
    "customer_alpha",
    "customer_beta",
    "vip_client"
]

proprietary_tier := "PROPRIETARY" {
    some customer in proprietary_customers
    contains(lower(input.query), customer)
}

# Competitive intelligence protection
proprietary_tier := "PROPRIETARY" {
    competitive_terms := [
        "market share",
        "pricing strategy",
        "product roadmap",
        "acquisition target"
    ]
    some term in competitive_terms
    contains(lower(input.query), term)
}

proprietary_reason := reason {
    proprietary_tier == "PROPRIETARY"
    reason := "Matched company-specific sensitivity rules"
}
```

---

## Advanced Patterns

### Time-Based Rules

```rego
# Embargo: Sensitive until announcement
proprietary_tier := "PROPRIETARY" {
    contains(lower(input.query), "new product launch")
    
    # Parse current time
    time.now_ns() < time.parse_rfc3339_ns("2026-03-01T00:00:00Z")
}

proprietary_reason := "Product information under embargo until March 2026" {
    contains(lower(input.query), "new product launch")
    time.now_ns() < time.parse_rfc3339_ns("2026-03-01T00:00:00Z")
}
```

### Context-Aware Rules

```rego
# More permissive for specific users
internal_tier := "INTERNAL" {
    # Would normally be PROPRIETARY
    contains(lower(input.query), "internal infrastructure")
    
    # But user has elevated permissions
    input.context.user_id in data.elevated_users
}

# More restrictive in certain projects
proprietary_tier := "PROPRIETARY" {
    # Normally PUBLIC query
    contains(lower(input.query), "python tutorial")
    
    # But within sensitive project context
    input.context.project == "classified_research"
}
```

### Multi-Factor Rules

```rego
# Require multiple conditions
proprietary_tier := "PROPRIETARY" {
    # Condition 1: Contains sensitive term
    contains(lower(input.query), "customer")
    
    # Condition 2: In production environment
    input.context.environment == "production"
    
    # Condition 3: During business hours (higher risk)
    hour := time.clock([time.now_ns()])[0]
    hour >= 9
    hour <= 17
}
```

### Confidence Scoring

```rego
# Variable confidence based on matches
classification[result] {
    matched_terms := [term | 
        term := proprietary_terms[_]
        contains(lower(input.query), term)
    ]
    
    count(matched_terms) > 0
    
    # More matches = higher confidence
    confidence := min([1.0, count(matched_terms) * 0.3])
    
    result := {
        "tier": "PROPRIETARY",
        "confidence": confidence,
        "reasoning": sprintf("Matched %d proprietary terms", [count(matched_terms)])
    }
}
```

---

## Testing Framework

### Unit Tests

```rego
# policies/base_test.rego
package lacuna.classification

import future.keywords.if

test_proprietary_project_detection if {
    result := classification with input as {
        "query": "How do we deploy?",
        "context": {"project": "project_apollo"}
    }
    result.tier == "PROPRIETARY"
}

test_customer_reference_detection if {
    result := classification with input as {
        "query": "What did customer_alpha request?"
    }
    result.tier == "PROPRIETARY"
}

test_public_query if {
    result := classification with input as {
        "query": "What's the latest Python version?"
    }
    result.tier == "PUBLIC"
}

test_internal_process if {
    result := classification with input as {
        "query": "How do we deploy to staging?"
    }
    result.tier == "INTERNAL"
}
```

**Run tests**:
```bash
# All tests
opa test policies/ -v

# Specific policy
opa test policies/healthcare_test.rego -v

# With coverage
opa test policies/ --coverage --format=json
```

### Integration Testing

```python
# tests/test_opa_integration.py
import pytest
from lacuna.plugins import OPAPlugin

@pytest.fixture
def opa_plugin():
    return OPAPlugin(
        endpoint="http://localhost:8181",
        policy_path="lacuna/classification"
    )

def test_proprietary_classification(opa_plugin):
    """Test OPA correctly classifies proprietary queries."""
    result = opa_plugin.classify(
        query="How do we handle customer_alpha data?",
        context={"project": "production"}
    )
    
    assert result.tier == "PROPRIETARY"
    assert result.confidence >= 0.9
    assert "customer" in result.reasoning.lower()

def test_public_classification(opa_plugin):
    """Test OPA correctly classifies public queries."""
    result = opa_plugin.classify(
        query="What's the latest Rust version?",
        context={}
    )
    
    assert result.tier == "PUBLIC"

def test_policy_timeout_handling(opa_plugin):
    """Test graceful handling of OPA timeouts."""
    opa_plugin.timeout = 0.001  # Very short timeout
    
    result = opa_plugin.classify(
        query="Test query",
        context={}
    )
    
    # Should fallback gracefully
    assert result is None or result.tier == "PROPRIETARY"
```

---

## Policy Deployment

### GitOps Workflow

```
Developer writes policy → PR → Review → Merge → CI/CD → Deploy
     (Rego file)                           ↓
                                     OPA Test Suite
                                           ↓
                                     Policy Validation
                                           ↓
                                    Deploy to OPA Server
```

**GitHub Actions example**:

```yaml
# .github/workflows/policy-ci.yml
name: OPA Policy CI

on:
  pull_request:
    paths:
      - 'policies/**'
  push:
    branches: [main]
    paths:
      - 'policies/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup OPA
        run: |
          curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
          chmod +x opa
          sudo mv opa /usr/local/bin/
      
      - name: Run OPA Tests
        run: opa test policies/ -v
      
      - name: Check Coverage
        run: |
          opa test policies/ --coverage --format=json > coverage.json
          COVERAGE=$(jq '.coverage' coverage.json)
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage too low: $COVERAGE%"
            exit 1
          fi
      
      - name: Validate Policy Syntax
        run: opa check policies/

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to OPA ConfigMap
        run: |
          kubectl create configmap opa-policies \
            --from-file=policies/ \
            --dry-run=client -o yaml | \
            kubectl apply -f -
          
          # Reload OPA
          kubectl rollout restart deployment/opa -n lacuna
```

### Versioning Policies

```rego
# Include version metadata
package lacuna.classification

metadata := {
    "version": "1.2.0",
    "last_updated": "2026-01-19",
    "author": "compliance-team",
    "description": "HIPAA-compliant classification rules"
}

# Return version in results
classification[result] {
    # ... classification logic ...
    result := {
        "tier": tier,
        "confidence": confidence,
        "reasoning": reasoning,
        "metadata": {
            "policy_version": metadata.version
        }
    }
}
```

---

## Monitoring & Debugging

### OPA Metrics

```prometheus
# Policy evaluation latency
opa_http_request_duration_seconds_bucket{path="/v1/data/lacuna/classification"}

# Policy evaluation count
opa_http_request_total{path="/v1/data/lacuna/classification"}

# Policy errors
opa_http_request_error_total
```

### Debug Mode

```bash
# Enable OPA decision logging
docker run -p 8181:8181 \
  -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest \
  run --server --addr :8181 \
  --log-level debug \
  --log-format json \
  /policies
```

**Query decision log**:
```bash
curl http://localhost:8181/logs
```

### Policy Explanation

```bash
# Explain why a decision was made
curl -X POST http://localhost:8181/v1/data/lacuna/classification/classification \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "How do we handle patient data?",
    "context": {"project": "healthcare"}
  }' \
  --explain notes
```

---

## Best Practices

### 1. Start Simple, Add Complexity Gradually

```rego
# ✅ Good: Clear, simple rules
proprietary_tier := "PROPRIETARY" {
    input.context.project in ["apollo", "artemis"]
}

# ❌ Bad: Overly complex on day 1
proprietary_tier := "PROPRIETARY" {
    projects := [p | p := data.projects[_]; p.sensitivity == "high"]
    contexts := [c | c := input.context.tags[_]; c.level > 5]
    count(projects) > 0
    count(contexts) > 0
    time.now_ns() > time.parse_rfc3339_ns(data.embargo_dates[input.context.project])
}
```

### 2. Use Descriptive Rule Names

```rego
# ✅ Good: Self-documenting
proprietary_tier := "PROPRIETARY" {
    contains_phi_indicators
}

contains_phi_indicators {
    phi_terms := ["patient", "diagnosis", "medical record"]
    some term in phi_terms
    contains(lower(input.query), term)
}

# ❌ Bad: Unclear
proprietary_tier := "PROPRIETARY" {
    check1
}

check1 {
    data.terms[_] == "patient"
}
```

### 3. Always Provide Reasoning

```rego
# ✅ Good: Explains decision
proprietary_reason := reason {
    matched := [term | 
        term := phi_terms[_]
        contains(lower(input.query), term)
    ]
    reason := sprintf("Matched PHI terms: %v", [matched])
}

# ❌ Bad: No explanation
proprietary_reason := "Proprietary" {
    proprietary_tier == "PROPRIETARY"
}
```

### 4. Test Edge Cases

```rego
test_case_sensitivity if {
    # Should match regardless of case
    result1 := classification with input as {"query": "PATIENT data"}
    result2 := classification with input as {"query": "patient data"}
    result1.tier == result2.tier
}

test_partial_matches if {
    # "patients" should match "patient" rule
    result := classification with input as {"query": "How many patients?"}
    result.tier == "PROPRIETARY"
}

test_empty_context if {
    # Should not crash on missing context
    result := classification with input as {"query": "test"}
    result.tier in ["PROPRIETARY", "INTERNAL", "PUBLIC"]
}
```

### 5. Version and Document Policies

```rego
package lacuna.classification

# Policy metadata (required)
metadata := {
    "version": "2.1.0",
    "effective_date": "2026-01-19",
    "author": "security-team@company.com",
    "description": "Classification rules for healthcare data (HIPAA compliant)",
    "changelog": [
        "2.1.0: Added MRN pattern detection",
        "2.0.0: Reorganized for clarity",
        "1.0.0: Initial version"
    ]
}
```

---

## Troubleshooting

### Policy Not Applied

**Symptom**: OPA policy not affecting classifications

**Diagnosis**:
```bash
# Check OPA is running
curl http://localhost:8181/health

# Check policy is loaded
curl http://localhost:8181/v1/policies

# Test policy directly
curl -X POST http://localhost:8181/v1/data/lacuna/classification/classification \
  -d '{"input": {"query": "test", "context": {}}}'
```

**Solutions**:
1. Verify OPA endpoint in Lacuna config
2. Check policy package name matches config
3. Verify policy syntax: `opa check policies/`
4. Check plugin priority (OPA should be high priority)

### High Latency

**Symptom**: OPA policy evaluation >50ms

**Diagnosis**:
```rego
# Add timing annotations
package lacuna.classification

classification[result] {
    start := time.now_ns()
    # ... policy logic ...
    end := time.now_ns()
    duration_ms := (end - start) / 1000000
    
    trace(sprintf("Policy evaluation took %d ms", [duration_ms]))
    # ... return result ...
}
```

**Solutions**:
1. Simplify complex rules
2. Use OPA's built-in functions (faster than custom)
3. Cache expensive operations
4. Consider pre-computing data lookups

### Conflicting Rules

**Symptom**: Multiple tiers returned

**Diagnosis**:
```bash
# Check for multiple matching rules
opa eval --data policies/ \
  --input input.json \
  'data.lacuna.classification.classification' \
  --explain full
```

**Solutions**:
1. Use rule prioritization
2. Add explicit exclusions: `not internal_tier`
3. Consolidate overlapping rules
4. Use else statements for fallbacks

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Classification pipeline design
- [PLUGINS.md](PLUGINS.md) - Plugin ecosystem and OPA integration
- [DEPLOYMENT.md](DEPLOYMENT.md) - OPA deployment in production
- [LINEAGE.md](LINEAGE.md) - Policy decision audit trail

---

*Policy-as-Code enables compliance teams to control classification rules without engineering bottlenecks.*
