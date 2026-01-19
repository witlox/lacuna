# ISO 27001 Audit Logging

## Overview

Lacuna provides **ISO 27001/27002-compliant audit logging** with:
- Tamper-evident hash chains
- Complete provenance capture (who, what, when, why, how)
- Append-only storage with integrity verification
- Real-time alerting for critical events
- 7-year retention with automated archival
- Compliance report generation

## ISO 27001 Control Mapping

### A.9.4: System and Application Access Control

**A.9.4.1 Information access restriction**

Lacuna logs:
- Every data access attempt (successful and failed)
- Classification decisions for all accessed data
- Policy evaluations (allow/deny with reasoning)
- User identity, role, and clearance level

**A.9.4.5 Access to source code**

Lacuna logs:
- Access to code repositories
- Execution of transformation code
- dbt model runs with complete SQL
- Custom script executions

### A.12.4: Logging and Monitoring

**A.12.4.1 Event logging**

Lacuna captures:
- User IDs and timestamps (NTP-synchronized)
- Successful/failed authentication
- Data and system access attempts
- System configuration changes
- Privileged account usage
- Audit trail function activation

**A.12.4.2 Protection of log information**

Lacuna ensures:
- Append-only storage (no updates/deletes)
- Hash chain prevents tampering
- Separate credentials for audit access
- Encryption at rest and in transit
- Regular integrity verification

**A.12.4.3 Administrator and operator logs**

Lacuna tracks:
- All policy changes (create, update, delete)
- User permission grants/revokes
- Configuration modifications
- System maintenance actions

**A.12.4.4 Clock synchronization**

Lacuna synchronizes:
- All timestamps via NTP
- Fallback warnings if NTP fails
- Timezone-aware storage (UTC)

### A.18.1: Compliance with Legal and Contractual Requirements

**A.18.1.3 Protection of records**

Lacuna provides:
- 7-year minimum retention
- Automated archival to cold storage
- Tamper-evident storage
- Compliance report generation

## Audit Record Schema

### Core Audit Record

Every event in Lacuna generates a comprehensive audit record:

```python
@dataclass
class AuditRecord:
    """ISO 27001-compliant audit record."""
    
    # Core Identity
    event_id: str  # UUID for unique identification
    timestamp: datetime  # ISO 8601, NTP-synchronized
    event_type: EventType  # Categorized event
    severity: Severity  # INFO, WARNING, ERROR, CRITICAL
    
    # Actor Identification
    user_id: str  # Who performed the action
    user_session_id: str  # Session identifier
    user_ip_address: str  # Source IP
    user_role: str  # Role/clearance level
    user_department: Optional[str]
    
    # Target Resource
    resource_type: str  # "dataset", "table", "file", "query"
    resource_id: str  # Unique identifier
    resource_classification: Optional[str]  # PROPRIETARY/INTERNAL/PUBLIC
    resource_tags: List[str]  # PII, PHI, FINANCIAL, etc.
    
    # Action Details
    action: str  # "read", "write", "classify", "export"
    action_result: str  # "success", "denied", "error"
    action_metadata: Dict[str, Any]  # Action-specific details
    
    # Policy/Governance
    policy_id: Optional[str]  # Which policy was evaluated
    policy_version: Optional[str]  # Policy version
    classification_tier: Optional[str]
    classification_confidence: Optional[float]
    classification_reasoning: Optional[str]
    
    # Lineage/Provenance
    parent_event_id: Optional[str]  # For chained operations
    lineage_chain: List[str]  # Upstream data sources
    
    # Compliance Metadata
    compliance_flags: List[str]  # GDPR, HIPAA, SOX, etc.
    retention_period_days: int  # Default: 2555 (7 years)
    
    # Tamper Detection
    previous_record_hash: Optional[str]  # Hash of previous record
    record_hash: str  # Hash of this record
    signature: Optional[str]  # Digital signature
    
    # System Context
    system_id: str
    system_version: str
```

### Event Types

```python
class EventType(Enum):
    # Access Events (A.9.4.1)
    DATA_ACCESS = "data.access"
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # Classification Events
    CLASSIFICATION_AUTO = "classification.automatic"
    CLASSIFICATION_MANUAL = "classification.manual_override"
    CLASSIFICATION_POLICY_CHANGE = "classification.policy_change"
    
    # Policy Events
    POLICY_EVALUATION = "policy.evaluation"
    POLICY_ALLOW = "policy.allow"
    POLICY_DENY = "policy.deny"
    POLICY_EXCEPTION = "policy.exception_granted"
    
    # Administrative Events (A.12.4.3)
    ADMIN_POLICY_CREATE = "admin.policy.create"
    ADMIN_POLICY_UPDATE = "admin.policy.update"
    ADMIN_POLICY_DELETE = "admin.policy.delete"
    ADMIN_USER_GRANT = "admin.user.grant_access"
    ADMIN_USER_REVOKE = "admin.user.revoke_access"
    
    # Authentication Events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    
    # System Events
    SYSTEM_CONFIG_CHANGE = "system.config.change"
    AUDIT_LOG_ACCESS = "audit.log.access"
```

## Storage Architecture

### PostgreSQL Backend

Lacuna uses PostgreSQL with:
- **Partitioned tables** by month for performance
- **Append-only constraints** (no UPDATE/DELETE)
- **Hash chain** linking records chronologically
- **Indexes** optimized for audit queries

```sql
CREATE TABLE audit_log (
    event_id UUID PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    
    user_id VARCHAR(255) NOT NULL,
    user_session_id VARCHAR(255),
    user_ip_address INET,
    user_role VARCHAR(100),
    
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(500) NOT NULL,
    resource_classification VARCHAR(20),
    resource_tags TEXT[],
    
    action VARCHAR(100) NOT NULL,
    action_result VARCHAR(20) NOT NULL,
    action_metadata JSONB,
    
    policy_id VARCHAR(100),
    policy_version VARCHAR(50),
    classification_tier VARCHAR(20),
    classification_confidence FLOAT,
    classification_reasoning TEXT,
    
    parent_event_id UUID,
    lineage_chain TEXT[],
    
    compliance_flags TEXT[],
    retention_period_days INTEGER DEFAULT 2555,
    
    previous_record_hash VARCHAR(64),
    record_hash VARCHAR(64) NOT NULL,
    signature TEXT,
    
    system_id VARCHAR(100),
    system_version VARCHAR(50),
    
    CONSTRAINT no_updates CHECK (true)
) PARTITION BY RANGE (timestamp);

-- Prevent DELETE operations
CREATE RULE audit_log_no_delete AS 
    ON DELETE TO audit_log DO INSTEAD NOTHING;

-- Prevent UPDATE operations  
CREATE RULE audit_log_no_update AS 
    ON UPDATE TO audit_log DO INSTEAD NOTHING;

-- Indexes for common queries
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_id, timestamp DESC);
CREATE INDEX idx_audit_classification ON audit_log(resource_classification, timestamp DESC);
CREATE INDEX idx_audit_tags ON audit_log USING GIN(resource_tags);
```

### Hash Chain

Every record links to previous via cryptographic hash:

```
Record 1: hash = SHA256(record_1_data)
Record 2: hash = SHA256(record_2_data + Record_1.hash)
Record 3: hash = SHA256(record_3_data + Record_2.hash)
...

Breaking the chain = Tampering detected
```

Verification:
```python
def verify_integrity(start_time: datetime) -> bool:
    """Verify hash chain integrity."""
    records = query_records(start_time, order="ASC")
    
    previous_hash = None
    for record in records:
        # Check link to previous
        if previous_hash and record.previous_record_hash != previous_hash:
            return False  # Chain broken!
        
        # Verify this record's hash
        computed = compute_hash(record)
        if computed != record.record_hash:
            return False  # Record modified!
        
        previous_hash = record.record_hash
    
    return True  # Chain intact
```

## Audit Workflow Example

### Scenario: User Exports Customer Data

```python
# User code
customers = pd.read_csv("customers.csv")
customers.to_csv("~/Downloads/export.csv")
```

### Generated Audit Trail

**Event 1: Data Access Attempt**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2025-01-17T10:30:00Z",
  "event_type": "DATA_ACCESS",
  "severity": "INFO",
  "user_id": "alice@example.com",
  "user_role": "data_analyst",
  "resource_type": "file",
  "resource_id": "customers.csv",
  "action": "read",
  "action_result": "attempting"
}
```

**Event 2: Classification Decision**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440002",
  "timestamp": "2025-01-17T10:30:00.123Z",
  "event_type": "CLASSIFICATION_AUTO",
  "severity": "INFO",
  "user_id": "alice@example.com",
  "resource_type": "file",
  "resource_id": "customers.csv",
  "resource_classification": "PROPRIETARY",
  "resource_tags": ["PII", "GDPR", "CUSTOMER_DATA"],
  "action": "classify",
  "action_result": "success",
  "classification_tier": "PROPRIETARY",
  "classification_confidence": 0.95,
  "classification_reasoning": "File contains email, phone columns (PII detected)",
  "parent_event_id": "550e8400-e29b-41d4-a716-446655440001",
  "previous_record_hash": "a3c9f..."
}
```

**Event 3: Policy Evaluation**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440003",
  "timestamp": "2025-01-17T10:30:00.145Z",
  "event_type": "POLICY_DENY",
  "severity": "WARNING",
  "user_id": "alice@example.com",
  "resource_type": "file",
  "resource_id": "customers.csv",
  "resource_classification": "PROPRIETARY",
  "action": "export",
  "action_result": "denied",
  "action_metadata": {
    "destination": "~/Downloads/export.csv",
    "destination_encrypted": false,
    "policy_reasoning": "Cannot export PROPRIETARY data to unmanaged location"
  },
  "policy_id": "P-2024-001",
  "policy_version": "1.2.0",
  "parent_event_id": "550e8400-e29b-41d4-a716-446655440002",
  "compliance_flags": ["GDPR", "CCPA"],
  "previous_record_hash": "b7f1e..."
}
```

**Event 4: User Override Attempt** (if user requests exception)
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440004",
  "timestamp": "2025-01-17T10:35:00Z",
  "event_type": "POLICY_EXCEPTION",
  "severity": "WARNING",
  "user_id": "alice@example.com",
  "resource_type": "file",
  "resource_id": "customers.csv",
  "action": "request_exception",
  "action_result": "pending_approval",
  "action_metadata": {
    "business_justification": "Board presentation Q4 metrics",
    "requested_approver": "data-steward@example.com",
    "duration_hours": 2
  },
  "parent_event_id": "550e8400-e29b-41d4-a716-446655440003",
  "previous_record_hash": "c2d4f..."
}
```

## Real-Time Alerting

### Alert Rules

Lacuna monitors audit stream for critical patterns:

```python
class AlertRule:
    """Define alerting conditions."""
    
    name: str
    condition: Callable[[List[AuditRecord]], bool]
    severity: Severity
    notification_channels: List[str]
    window_minutes: int = 5

# Example rules
ALERT_RULES = [
    AlertRule(
        name="repeated_denials",
        condition=lambda events: count_denials(events, minutes=5) >= 5,
        severity=Severity.CRITICAL,
        notification_channels=["security@example.com", "slack:#security"]
    ),
    AlertRule(
        name="proprietary_export_attempt",
        condition=lambda event: (
            event.event_type == EventType.DATA_EXPORT and
            event.resource_classification == "PROPRIETARY"
        ),
        severity=Severity.WARNING,
        notification_channels=["governance@example.com"]
    ),
    AlertRule(
        name="admin_policy_change",
        condition=lambda event: event.event_type.value.startswith("admin.policy"),
        severity=Severity.WARNING,
        notification_channels=["governance@example.com", "security@example.com"]
    ),
    AlertRule(
        name="integrity_check_failure",
        condition=lambda event: (
            event.event_type == EventType.SYSTEM_EVENT and
            "integrity_failure" in event.action_metadata
        ),
        severity=Severity.CRITICAL,
        notification_channels=["security@example.com", "on-call"]
    )
]
```

### Alert Example

```
🚨 CRITICAL ALERT: repeated_denials

User: alice@example.com
Pattern: 5 policy denials in 3 minutes
Resources: customers.csv, sales.csv, partners.csv
Action: export attempts to ~/Downloads/

Possible causes:
• User unaware of governance policies
• Misconfigured classification
• Attempted data exfiltration

Recommended actions:
1. Contact user for clarification
2. Review user's recent activity
3. Verify classification accuracy
4. Consider security incident response

Event IDs: 550e8400-..., 661f9511-..., 772g0622-...
Time: 2025-01-17 10:30-10:33 UTC
```

## Retention and Archival

### Retention Tiers

| Tier | Duration | Storage | Access Speed | Cost |
|------|----------|---------|--------------|------|
| **Hot** | 0-90 days | PostgreSQL | <100ms | High |
| **Warm** | 90 days - 1 year | Compressed PostgreSQL | <1s | Medium |
| **Cold** | 1-7 years | S3 Glacier / Tape | Minutes | Low |

### Automated Archival

```python
# Runs daily as scheduled job
def archive_old_records():
    """Archive records older than 90 days."""
    cutoff = datetime.now() - timedelta(days=90)
    
    # Query records to archive
    records = query_audit_log(end_date=cutoff)
    
    # Verify integrity before archival
    if not verify_integrity(start_time=min(r.timestamp for r in records)):
        raise Exception("Cannot archive: integrity check failed")
    
    # Create encrypted archive
    archive_file = create_archive(
        records=records,
        compression="gzip",
        encryption="AES-256-CBC"
    )
    
    # Upload to cold storage
    upload_to_glacier(archive_file)
    
    # Verify cold storage
    if not verify_cold_storage(archive_file):
        raise Exception("Cannot delete from hot storage: verification failed")
    
    # Delete from hot storage (only after verified)
    delete_archived_records(records)
```

### Retrieval from Archive

```python
def retrieve_from_archive(start_date: datetime, end_date: datetime) -> List[AuditRecord]:
    """Retrieve archived records (slow operation)."""
    
    # Find relevant archive files
    archives = find_archives_for_period(start_date, end_date)
    
    # Download from Glacier (may take hours)
    for archive in archives:
        initiate_retrieval(archive)
    
    # Wait for retrieval
    wait_for_retrieval_completion(archives)
    
    # Download, decrypt, decompress
    records = []
    for archive in archives:
        archive_records = extract_archive(archive)
        records.extend([
            r for r in archive_records
            if start_date <= r.timestamp <= end_date
        ])
    
    return records
```

## Compliance Reporting

### A.9.4 Report: Access Control

```python
from lacuna.compliance import ISO27001Reporter

reporter = ISO27001Reporter()

# Generate A.9.4 report
report = reporter.generate_a_9_4_report(
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(report)
```

**Output:**
```
ISO 27001 Control A.9.4 Audit Report
Period: 2024-01-01 to 2024-12-31

1. ACCESS SUMMARY
Total access attempts: 1,245,892
Successful: 1,238,451 (99.4%)
Failed/Denied: 7,441 (0.6%)

2. USER ACCESS PATTERNS
Top Users by Access Count:
- alice@example.com: 45,231 accesses (98.2% success)
- bob@example.com: 38,912 accesses (99.1% success)
- charlie@example.com: 32,445 accesses (97.8% success)

3. FAILED ACCESS ATTEMPTS
Policy Denials: 6,822 (91.7% of failures)
Authentication Failures: 445 (6.0%)
System Errors: 174 (2.3%)

Top Denied Resources:
- customers.csv: 2,341 denials (PII export attempts)
- financial_data.db: 1,892 denials (insufficient clearance)
- strategic_plans/: 981 denials (department restrictions)

4. PRIVILEGE CHANGES
User Grants: 145
User Revocations: 67
Clearance Upgrades: 23
Clearance Downgrades: 12

5. SENSITIVE DATA ACCESS
PROPRIETARY tier: 234,567 accesses (18.8%)
- 99.2% by authorized users
- 0.8% denied (policy violations)

PII Data Access: 89,234 instances
- All logged with lineage
- 127 exceptions granted
- 0 unauthorized access detected

6. COMPLIANCE ISSUES
Critical: 0
High: 3 (under investigation)
Medium: 12 (resolved)
Low: 45 (normal variation)
```

### GDPR Report

```python
# Generate GDPR compliance report
gdpr_report = reporter.generate_gdpr_report(
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

**Output:**
```
GDPR Compliance Report
Period: 2024-01-01 to 2024-12-31

ARTICLE 5: Principles
✓ Lawfulness: All PII access logged with purpose
✓ Fairness: User notifications implemented
✓ Transparency: Audit trail available to data subjects
✓ Purpose Limitation: Purpose tracked for all access
✓ Data Minimization: Aggregation preferred where possible
✓ Accuracy: Quality checks logged
✓ Storage Limitation: Retention policies enforced
✓ Integrity: Hash chain verified

ARTICLE 30: Records of Processing
Total PII Processing Activities: 89,234
- Customer Data: 67,891
- Employee Data: 18,234
- Partner Data: 3,109

All activities logged with:
✓ Purpose
✓ Data categories
✓ Recipients
✓ Retention periods
✓ Security measures

ARTICLE 32: Security of Processing
✓ Pseudonymization: Available and tracked
✓ Encryption: Enforced for PROPRIETARY data
✓ Integrity: Hash chain verification
✓ Availability: 99.97% uptime
✓ Testing: Monthly integrity checks

DATA SUBJECT RIGHTS
Access Requests (Art. 15): 234 (avg response: 3.2 days)
Rectification Requests (Art. 16): 45 (all completed)
Erasure Requests (Art. 17): 12 (all completed)
Restriction Requests (Art. 18): 5 (all completed)
Portability Requests (Art. 20): 8 (all completed)

BREACHES
Personal Data Breaches: 0
Near-Miss Incidents: 3 (prevented by Lacuna)
```

## Querying Audit Logs

### Query Interface

```python
from lacuna.audit import AuditQuery

# Query user activity
user_activity = AuditQuery.for_user(
    user_id="alice@example.com",
    start_date="2025-01-01",
    end_date="2025-01-31"
)

print(f"Total events: {len(user_activity)}")
print(f"Access attempts: {user_activity.count(event_type='DATA_ACCESS')}")
print(f"Denials: {user_activity.count(action_result='denied')}")

# Query resource access
resource_access = AuditQuery.for_resource(
    resource_id="customers.csv",
    start_date="2025-01-01",
    end_date="2025-01-31"
)

print(f"Accessed by {resource_access.unique_users()} users")
print(f"Most common action: {resource_access.most_common_action()}")

# Query policy violations
violations = AuditQuery.violations(
    start_date="2025-01-01",
    end_date="2025-01-31"
)

print(f"Total violations: {len(violations)}")
print(f"By policy: {violations.group_by('policy_id')}")

# Complex query
high_risk_activity = AuditQuery.where(
    resource_classification="PROPRIETARY",
    action="export",
    user_role="contractor"  # External contractors
).and_where(
    action_result="success"  # Actually succeeded
).order_by("timestamp", desc=True)
```

### Accessing Audit Logs is Audited

```python
# Querying audit logs generates its own audit event
query_result = AuditQuery.for_user("alice@example.com", ...)

# This creates an audit record:
{
  "event_type": "AUDIT_LOG_ACCESS",
  "user_id": "admin@example.com",
  "resource_type": "audit_log",
  "resource_id": "user_activity:alice@example.com",
  "action": "query",
  "action_result": "success",
  "action_metadata": {
    "records_returned": 1234,
    "query_parameters": {...}
  }
}
```

**Important**: Only authorized roles (auditor, compliance_officer, security_admin) can access audit logs.

## Best Practices

### 1. Regular Integrity Verification

```bash
# Run weekly
lacuna audit verify-integrity --since 2025-01-01

# Output
✓ Verified 1,245,892 records
✓ Hash chain intact
✓ No tampering detected
✓ Last verification: 2025-01-17 10:00 UTC
```

### 2. Test Archival and Retrieval

```bash
# Quarterly test
lacuna audit test-archive-retrieval --date 2024-10-01

# Ensures:
# - Archives can be retrieved
# - Decryption works
# - Data integrity preserved
# - Retrieval time acceptable
```

### 3. Review Alert Rules

```python
# Monthly review
from lacuna.audit import AlertMetrics

metrics = AlertMetrics(period="last_30_days")

print(f"Alerts fired: {metrics.total_alerts}")
print(f"False positives: {metrics.false_positive_rate}%")
print(f"Response time: {metrics.avg_response_time_minutes} min")

# Adjust thresholds if needed
```

### 4. Compliance Report Automation

```yaml
# Schedule compliance reports
compliance_reports:
  iso27001_a94:
    frequency: monthly
    recipients: [compliance@example.com]
    
  gdpr:
    frequency: quarterly
    recipients: [dpo@example.com, legal@example.com]
  
  hipaa:
    frequency: annually
    recipients: [compliance@example.com, security@example.com]
```

## Summary

Lacuna's audit logging provides:

✓ **ISO 27001 compliance** out-of-the-box
✓ **Tamper-evident** storage with hash chains
✓ **Complete provenance** for every data operation
✓ **Real-time alerting** for security events
✓ **Automated archival** with 7-year retention
✓ **Compliance reports** ready for auditors
✓ **Query interface** for investigations

**No manual effort required.** Audit logging is automatic, comprehensive, and ready for any compliance audit.
