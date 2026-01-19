# Data Governance with Lacuna

## Self-Service Governance Model

### The Challenge

Traditional data governance faces a fundamental tension:

**Centralized Control**
- ✓ Consistent policy enforcement
- ✓ Clear audit trails
- ✗ Bottlenecks slow innovation
- ✗ Users find workarounds

**Complete Self-Service**
- ✓ Fast, autonomous data access
- ✓ Innovation enabled
- ✗ Compliance violations
- ✗ Data leaks and shadow IT

**Lacuna's Solution**: Central teams define policies, users see violations in real-time and can self-correct

### Core Principles

#### 1. Policy-as-Code

Policies are defined declaratively in version control, not hidden in application logic:

```rego
# policies/pii_export.rego
package governance

# Default deny for safety
default allow_export = false

# Allow export if all conditions met
allow_export {
    # Data is not classified as PROPRIETARY
    input.classification != "PROPRIETARY"
    
    # OR user has explicit exemption
    not input.classification == "PROPRIETARY"
} {
    # OR destination is approved
    input.destination.type == "governed_storage"
    input.destination.encrypted == true
}

# Provide alternatives when denied
alternatives[msg] {
    not allow_export
    input.classification == "PROPRIETARY"
    msg := "Use anonymized version: lacuna.anonymize(data, pii_columns)"
} {
    not allow_export
    input.classification == "PROPRIETARY"
    msg := sprintf("Save to governed location: %s", [approved_paths[_]])
}
```

**Benefits:**
- Policies are versioned and auditable
- Changes go through code review
- Rollback is trivial (git revert)
- Testing is automated

#### 2. Real-Time Feedback

Users see policy violations **before** they happen, with actionable guidance:

```python
# User attempts operation
df.to_csv("~/Downloads/customers.csv")

# Lacuna intercepts and evaluates
❌ Governance Policy Violation

Action: Export to ~/Downloads/customers.csv
Reason: Cannot export PROPRIETARY data to unmanaged location
Classification: PROPRIETARY
Tags: PII, GDPR

Why this matters:
- Contains customer PII (email, phone)
- Destination is not encrypted or monitored
- Violates GDPR data minimization principle

How to proceed:
1. Anonymize first:
   anon_df = lacuna.anonymize(df, columns=['email', 'phone', 'address'])
   anon_df.to_csv("~/Downloads/customers_anon.csv")

2. Use governed location:
   df.to_csv("/governed/workspace/customers.csv")
   # Automatically encrypted, access logged, retention enforced

3. Request exception (requires business justification):
   lacuna.request_exception(
       data=df,
       destination="~/Downloads/customers.csv",
       purpose="Customer analysis for Q4 board presentation",
       approver="data-steward@example.com"
   )

Policy: P-2024-001 (PII Export Restrictions)
Steward: data-governance@example.com
Documentation: https://governance.example.com/policies/P-2024-001
```

**Key insight:** This isn't just an error message—it's a **learning moment**. The user understands:
- What they're doing wrong
- Why the policy exists
- How to achieve their goal compliantly

#### 3. Classification Inheritance

Data classification propagates automatically through lineage:

```python
# Source data
customers = pd.read_csv("customers.csv")  # PROPRIETARY (PII)
sales = pd.read_csv("sales.csv")          # INTERNAL (revenue)

# Operation: Join
analysis = customers.merge(sales, on="customer_id")

# Result classification
print(analysis.lacuna_classification)
# → PROPRIETARY (inherits most restrictive parent)

print(analysis.lacuna_tags)
# → ['PII', 'GDPR', 'FINANCIAL']  (union of parent tags)

print(analysis.lacuna_lineage)
# → customers.csv → analysis
#   sales.csv → analysis

# Operation: Aggregation
summary = analysis.groupby('region')['revenue'].sum()

# Result classification (downgraded by aggregation)
print(summary.lacuna_classification)
# → INTERNAL (no individual PII in aggregates)

print(summary.lacuna_tags)
# → ['FINANCIAL', 'DERIVED_FROM_PII']  (provenance preserved)
```

**Classification Rules:**

1. **Joins**: Maximum classification of all sources
2. **Aggregations**: May downgrade if no individual PII remains
3. **Filters**: Inherit source classification
4. **Transformations**: Inherit unless explicitly anonymized
5. **Exports**: Classification travels with data

#### 4. Graduated Access Tiers

Not all data requires the same level of control:

| Tier | Definition | Examples | Routing | Retention |
|------|-----------|----------|---------|-----------|
| **PROPRIETARY** | Competitive secrets, regulated data | Customer PII, pricing algorithms, strategic plans | Local only, approval required for export | 7+ years |
| **INTERNAL** | Internal use, not competitively sensitive | Team processes, internal analytics, tool configurations | Internal systems, no external sharing | 1-3 years |
| **PUBLIC** | Publicly available or could be | Open-source code, published docs, public research | No restrictions | 1 year minimum |

**Why three tiers?**
- Two tiers (sensitive/not-sensitive) are too coarse—most data falls in middle
- Four+ tiers create confusion and classification paralysis
- Three tiers map naturally to organizational boundaries: external, internal, restricted

### Implementation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   User Data Operation                       │
│  (read, write, join, export, transform)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              1. Operation Interception                      │
│                                                             │
│  • File system: FUSE intercepts read/write                  │
│  • Databases: SQLAlchemy middleware                         │
│  • Notebooks: IPython magic commands                        │
│  • dbt: Post-hooks in models                                │
│  • APIs: HTTP proxy layer                                   │
│                                                             │
│  Captures: source, destination, action, user, context       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          2. Classification (3-layer pipeline)               │
│                                                             │
│  Layer 1: Heuristics (<1ms) - 90% of operations             │
│  ├─ File path patterns: /pii/*, /customer/*                 │
│  ├─ Column name patterns: email, ssn, credit_card           │
│  └─ Known sensitive terms from config                       │
│                                                             │
│  Layer 2: Embeddings (<10ms) - 8% of operations             │
│  ├─ Semantic similarity to known examples                   │
│  ├─ Pre-computed embedding cache                            │
│  └─ Vector search for closest match                         │
│                                                             │
│  Layer 3: LLM (<200ms) - 2% of operations                   │
│  ├─ Complex context-dependent reasoning                     │
│  ├─ Multi-source lineage analysis                           │
│  └─ Ambiguous cases requiring judgment                      │
│                                                             │
│  Output: Classification(tier, confidence, reasoning, tags)  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            3. Lineage & Provenance Tracking                 │
│                                                             │
│  • Extract lineage: source(s) → operation → destination     │
│  • Apply inheritance rules:                                 │
│    - Join: max(source classifications)                      │
│    - Aggregate: evaluate if PII preserved                   │
│    - Filter: inherit source                                 │
│  • Propagate tags: union of all source tags                 │
│  • Capture provenance:                                      │
│    - Who: user_id, role, session                            │
│    - What: operation type, sources, destination             │
│    - When: timestamp (NTP-synchronized)                     │
│    - Why: business purpose (if provided)                    │
│    - How: transformation code, quality checks               │
│                                                             │
│  Output: DataOperation(classification, lineage, provenance) │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              4. Policy Evaluation (OPA)                     │
│                                                             │
│  Query OPA with context:                                    │
│  {                                                          │
│    "action": "export",                                      │
│    "source": {                                              │
│      "classification": "PROPRIETARY",                       │
│      "tags": ["PII", "GDPR"]                                │
│    },                                                       │
│    "destination": {                                         │
│      "type": "file",                                        │
│      "path": "~/Downloads/export.csv",                      │
│      "encrypted": false                                     │
│    },                                                       │
│    "user": {                                                │
│      "id": "analyst_alice",                                 │
│      "role": "data_analyst",                                │
│      "clearance": "INTERNAL"                                │
│    },                                                       │
│    "lineage": ["customers.csv", "sales.csv"]                │
│  }                                                          │
│                                                             │
│  OPA returns:                                               │
│  {                                                          │
│    "allow": false,                                          │
│    "policy_id": "P-2024-001",                               │
│    "reasoning": "Cannot export PROPRIETARY data...",        │
│    "alternatives": [...]                                    │
│  }                                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              5. User Feedback & Execution                   │
│                                                             │
│  If ALLOW:                                                  │
│  ├─ Execute operation                                       │
│  ├─ Log to audit trail                                      │
│  └─ Update lineage graph                                    │
│                                                             │
│  If DENY:                                                   │
│  ├─ Block operation                                         │
│  ├─ Show detailed error with alternatives                   │
│  ├─ Log denial to audit trail                               │
│  └─ Track for policy improvement                            │
│                                                             │
│  User can:                                                  │
│  ├─ Follow suggested alternative                            │
│  ├─ Request exception with justification                    │
│  └─ Provide feedback on policy                              │
└─────────────────────────────────────────────────────────────┘
```

### Policy Management

#### Centralized Policy Definition

Policies are defined by governance team but distributed execution:

```rego
# policies/data_export.rego
package governance.export

import future.keywords.if
import future.keywords.in

# Policy metadata
metadata := {
    "id": "P-2024-001",
    "title": "PII Export Restrictions",
    "owner": "data-governance@example.com",
    "compliance": ["GDPR", "CCPA"],
    "version": "1.2.0",
    "last_updated": "2025-01-15"
}

# Helper: Check if data contains PII
contains_pii if {
    "PII" in input.source.tags
}

# Helper: Check if destination is approved
approved_destination if {
    input.destination.type == "governed_storage"
    input.destination.encrypted == true
}

approved_destination if {
    input.destination.type == "database"
    input.destination.classification_support == true
}

# Main policy: Allow export
default allow := false

allow if {
    # Public data can go anywhere
    input.source.classification == "PUBLIC"
}

allow if {
    # Internal data to internal systems
    input.source.classification == "INTERNAL"
    input.destination.scope == "internal"
}

allow if {
    # Proprietary data only to approved destinations
    input.source.classification == "PROPRIETARY"
    approved_destination
}

allow if {
    # Exception granted by data steward
    input.exception_approved == true
    input.exception_approver_role == "data_steward"
}

# Provide helpful alternatives when denied
alternatives[msg] {
    not allow
    contains_pii
    msg := "Anonymize PII: lacuna.anonymize(data, pii_columns=['email', 'phone', 'address'])"
}

alternatives[msg] {
    not allow
    input.destination.type == "file"
    msg := sprintf("Save to governed storage: %v", [approved_paths[0]])
}

alternatives[msg] {
    not allow
    msg := "Request exception: lacuna.request_exception(purpose='...', approver='data-steward@example.com')"
}

# List of approved export paths
approved_paths := [
    "/governed/workspace/",
    "/governed/reports/",
    "s3://company-governed-data/"
]
```

#### Federated Policy Ownership

Domain teams can define domain-specific policies:

```rego
# policies/marketing_domain.rego
package governance.domains.marketing

# Marketing team owns policies for marketing data
metadata := {
    "domain": "marketing",
    "owner": "marketing-data-lead@example.com",
    "inherits": ["governance.export"]  # Inherit corporate policies
}

# Domain-specific classification
classify_marketing_data[classification] {
    input.source.table_name == "campaigns"
    classification := {
        "tier": "INTERNAL",
        "tags": ["MARKETING", "CAMPAIGN_DATA"],
        "steward": "marketing-data-lead@example.com"
    }
}

classify_marketing_data[classification] {
    input.source.table_name == "customer_segments"
    classification := {
        "tier": "PROPRIETARY",  # Contains customer intelligence
        "tags": ["MARKETING", "PROPRIETARY", "CUSTOMER_INTELLIGENCE"],
        "steward": "marketing-data-lead@example.com"
    }
}

# Marketing-specific export rules
allow_marketing_export {
    input.source.tags[_] == "MARKETING"
    input.user.department == "marketing"
    input.destination.type == "marketing_automation_platform"
}
```

**Benefits of federated ownership:**
- Central governance team defines meta-policies (e.g., "PII requires approval")
- Domain teams define domain-specific rules (e.g., "marketing can export to HubSpot")
- Scales policy management as organization grows
- Domain expertise embedded in policies

### Exception Management

Sometimes users need to violate policies for legitimate reasons:

```python
from lacuna import request_exception

# User's code
customers_df = pd.read_csv("customers.csv")  # PROPRIETARY, PII

# Attempt export (will be denied)
customers_df.to_csv("~/Downloads/board_report.csv")
# ❌ Policy violation

# Request exception with business justification
exception = request_exception(
    operation={
        "action": "export",
        "source": "customers.csv",
        "destination": "~/Downloads/board_report.csv"
    },
    purpose="Board of Directors Q4 customer metrics presentation",
    business_justification="""
    Board requested customer growth metrics with specific examples.
    Report will be presented in secure board room, then destroyed.
    Duration: 2 hours (2025-01-20 14:00-16:00).
    """,
    approver="data-steward@example.com",
    duration_hours=2,
    conditions=[
        "File will be encrypted",
        "File will be deleted after presentation",
        "No electronic copies will be made"
    ]
)

# Approval workflow
# 1. Data steward receives notification
# 2. Reviews justification and conditions
# 3. Approves or denies with comments

# If approved, user receives:
✓ Exception Approved

Exception ID: EXC-2025-001
Approved by: jane.smith@example.com (Data Steward)
Valid: 2025-01-20 14:00 - 16:00 UTC
Conditions:
  • File must be encrypted (AES-256)
  • File must be deleted after use
  • No electronic distribution

To proceed:
customers_df.to_csv(
    "~/Downloads/board_report.csv",
    exception_id="EXC-2025-001",
    encrypt=True
)

Reminder: Exception expires at 16:00 UTC. 
File will be automatically deleted.
```

**Exception audit trail:**
- All exceptions logged with full justification
- Approver accountability
- Automatic expiration
- Compliance reports include exceptions

### Measuring Success

#### Governance Metrics

**Policy Effectiveness:**
```python
from lacuna.metrics import GovernanceMetrics

metrics = GovernanceMetrics(period="last_30_days")

print(f"Policy violation rate: {metrics.violation_rate}%")
# Target: <2% (users mostly comply voluntarily)

print(f"False positive rate: {metrics.false_positive_rate}%")
# Target: <5% (policies aren't too restrictive)

print(f"Average resolution time: {metrics.avg_resolution_time_minutes} min")
# Target: <10min (users find compliant paths quickly)

print(f"Exception request rate: {metrics.exception_rate}%")
# Target: <1% (policies are practical)
```

**User Satisfaction:**
```python
print(f"User satisfaction: {metrics.user_satisfaction}/5")
# Survey question: "Governance tools help me work efficiently"
# Target: >4.0/5

print(f"Workaround attempts: {metrics.workaround_attempts}")
# Detection: Operations that match workaround patterns
# Target: Trending downward
```

**Compliance Coverage:**
```python
print(f"Data coverage: {metrics.data_coverage_percent}%")
# % of data assets under policy management
# Target: >80%

print(f"Lineage completeness: {metrics.lineage_completeness_percent}%")
# % of data flows with complete lineage
# Target: >90% for critical data

print(f"Audit completeness: {metrics.audit_completeness}%")
# % of operations captured in audit log
# Target: 100% for regulated data
```

### Common Patterns

#### Pattern 1: Development vs Production

Different policies for different environments:

```rego
package governance.environment_aware

allow_looser_in_dev {
    input.environment == "development"
    input.source.classification == "PROPRIETARY"
    input.destination.type == "local_file"
    input.destination.path_prefix == "/tmp/"
}

# Stricter in production
allow_strict_in_prod {
    input.environment == "production"
    input.source.classification == "PROPRIETARY"
    input.destination.type == "governed_storage"
    input.destination.encrypted == true
}
```

#### Pattern 2: Time-Based Access

Data available for limited time after collection:

```rego
package governance.time_based

import time

# Customer data older than 90 days requires special access
requires_retention_approval {
    input.source.tags[_] == "CUSTOMER_DATA"
    data_age_days := time.diff_days(time.now_ns(), input.source.created_at)
    data_age_days > 90
    not input.user.role == "compliance_officer"
}
```

#### Pattern 3: Purpose-Based Access

Same data, different rules based on purpose:

```rego
package governance.purpose_based

allow_for_analytics {
    input.purpose == "analytics"
    input.source.tags[_] == "CUSTOMER_DATA"
    input.destination.type == "analytics_warehouse"
}

deny_for_marketing {
    input.purpose == "marketing"
    input.source.tags[_] == "CUSTOMER_DATA"
    not input.user.consent_management_certified == true
}
```

## Best Practices

### 1. Start Small, Scale Gradually

**Phase 1**: Single team, 5 policies, critical data only
**Phase 2**: Multiple teams, 20 policies, most data covered
**Phase 3**: Enterprise-wide, 50+ policies, all data governed

**Don't try to govern everything on day 1.**

### 2. Make Compliant Paths Easier

**Bad**: Block everything, force exception requests
**Good**: Provide pre-approved alternatives that are easier than non-compliant paths

Example:
```python
# Don't just block
❌ Cannot export PII

# Provide easy alternative
❌ Cannot export raw PII
✓ Use pre-anonymized version:
  df_anon = lacuna.datasets.get("customers_anonymized")
  df_anon.to_csv("output.csv")  # This just works
```

### 3. Educate Through Errors

Every policy violation is a learning opportunity:

```python
# Bad error message
"Access denied: Policy P-123"

# Good error message
"""
❌ Cannot export customer emails to external service

Why: Customer emails are PII protected under GDPR
What: You're trying to send emails to api.external-service.com
Who: This requires customer consent + data processing agreement

Learn more: https://governance.example.com/gdpr/email-export
Questions: Ask #data-governance on Slack
"""
```

### 4. Measure and Improve

Track metrics, iterate on policies:

- **High violation rate**: Policies too strict or unclear
- **High false positive rate**: Classification needs tuning
- **High exception rate**: Policies don't match business needs
- **Low user satisfaction**: Friction too high

**Review quarterly, adjust based on data.**

### 5. Balance Control and Autonomy

```
Too much control → Shadow IT, workarounds, slow innovation
Too much freedom → Compliance violations, data leaks, audit failures

Sweet spot → Clear guardrails, self-service within bounds
```

Lacuna aims for the sweet spot: governance that **enables** rather than **blocks**.

## Integration Patterns

### With dbt

```yaml
# dbt_project.yml
on-run-start:
  - "{{ lacuna.register_run() }}"

on-run-end:
  - "{{ lacuna.verify_compliance() }}"

models:
  my_project:
    customer_analytics:
      +post-hook: "{{ lacuna.track_lineage() }}"
      +meta:
        classification: PROPRIETARY
        tags: [PII, CUSTOMER_DATA]
```

### With Databricks

```python
# Databricks notebook
spark.conf.set("spark.databricks.lacuna.enabled", "true")
spark.conf.set("spark.databricks.lacuna.policy_server", "http://lacuna:8181")

# All DataFrame operations automatically governed
df = spark.read.table("customers")  # Classification: PROPRIETARY
df.write.saveAsTable("analytics.customer_summary")  # Policy check
```

### With Jupyter

```python
# Cell 1: Load extension
%load_ext lacuna

# Cell 2: Configure
%lacuna config --policy-server http://lacuna:8181

# All subsequent cells are governed
df = pd.read_csv("customers.csv")  # Auto-classified
df.to_csv("output.csv")  # Policy-checked
```

## Troubleshooting

### "Classification takes too long"

**Symptom**: Operations delay 1-2 seconds

**Solution**: Check cache hit rate
```python
from lacuna.metrics import CacheMetrics
print(CacheMetrics.hit_rate())  # Should be >80%
```

If low, increase cache size or pre-warm cache:
```bash
lacuna cache warmup --config config.yaml
```

### "False positives blocking legitimate work"

**Symptom**: Users complain about unnecessary blocks

**Solution**: Review false positive reports
```python
from lacuna.admin import FalsePositiveReview
FalsePositiveReview.generate_report(days=7)
```

Adjust policies or classification thresholds based on patterns.

### "Lineage gaps"

**Symptom**: Downstream impact analysis incomplete

**Solution**: Add manual lineage registration for custom code
```python
from lacuna import register_lineage

# For operations Lacuna can't auto-detect
register_lineage(
    source=["raw_data.csv"],
    destination="processed_data.csv",
    operation="custom_transformation",
    code=open("transform.py").read()
)
```

## Summary

Lacuna's governance model achieves:

✓ **Self-service**: Users work autonomously within guardrails
✓ **Compliance**: Policies enforce automatically with audit trails
✓ **Transparency**: Users see exactly what/why/how of decisions
✓ **Learning**: System improves through user feedback
✓ **Scalability**: Federated policy ownership as org grows

**Key insight**: Governance isn't about saying "no"—it's about making "yes" safe, traceable, and compliant.
