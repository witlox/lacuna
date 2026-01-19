# Lacuna Architecture Overview

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User Layer                                 │
│  • Jupyter Notebooks  • VS Code  • CLI  • Web Dashboard             │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Lacuna Core Engine                              │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐      │
│  │  Operation      │  │ Classificat. │  │  Policy Engine     │      │
│  │  Interceptor    │→ │ Pipeline     │→ │  (OPA)             │      │
│  └─────────────────┘  └──────────────┘  └────────────────────┘      │
│           │                   │                     │               │
│           ↓                   ↓                     ↓               │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐      │
│  │  Lineage        │  │  Provenance  │  │  Audit Logger      │      │
│  │  Tracker        │  │  Capture     │  │  (PostgreSQL)      │      │
│  └─────────────────┘  └──────────────┘  └────────────────────┘      │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Integration Layer                               │
│  • dbt  • Databricks Unity Catalog  • Snowflake  • File Systems     │
└─────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

### 1. Operation Interceptor

**Purpose**: Capture all data operations before execution

**Implementations:**

**File System Operations (FUSE)**
```python
class LacunaFUSE:
    """Intercept file read/write operations."""
    
    def open(self, path: str, flags: int) -> int:
        # Before opening file
        operation = DataOperation(
            action="read" if flags & os.O_RDONLY else "write",
            resource_type="file",
            resource_id=path,
            user=get_current_user()
        )
        
        # Classify and check policy
        result = lacuna.evaluate(operation)
        
        if not result.allowed:
            raise PermissionError(result.reasoning)
        
        # Log and proceed
        lacuna.audit_log(operation, result)
        return os.open(path, flags)
```

**Database Operations (SQLAlchemy Middleware)**
```python
class LacunaQueryInterceptor:
    """Intercept SQL queries."""
    
    def before_cursor_execute(self, conn, cursor, statement, params, ...):
        # Parse SQL to extract tables
        tables = parse_sql_tables(statement)
        
        # Classify operation
        operation = DataOperation(
            action=get_sql_action(statement),  # SELECT, INSERT, UPDATE
            resource_type="table",
            resource_ids=tables,
            user=get_current_user()
        )
        
        # Check policy
        result = lacuna.evaluate(operation)
        
        if not result.allowed:
            raise PermissionError(f"Query denied: {result.reasoning}")
```

**Jupyter Notebook (IPython Magic)**
```python
@register_line_magic
@register_cell_magic
def lacuna(line, cell=None):
    """Intercept notebook operations."""
    
    # Extract operations from code
    operations = parse_python_code(cell or line)
    
    # Check each operation
    for op in operations:
        result = lacuna.evaluate(op)
        
        if not result.allowed:
            # Show inline warning
            display(HTML(format_warning(result)))
            return
    
    # Execute code
    get_ipython().run_cell(cell or line)
```

### 2. Classification Pipeline

**Three-Layer Design:**

```python
class ClassificationPipeline:
    """Three-layer classification with fallback."""
    
    def classify(self, operation: DataOperation) -> Classification:
        # Layer 1: Heuristics (<1ms)
        result = self.heuristic_classifier.classify(operation)
        if result.confidence > 0.9:
            return result
        
        # Layer 2: Embeddings (<10ms)
        result = self.embedding_classifier.classify(operation)
        if result.confidence > 0.8:
            return result
        
        # Layer 3: LLM (<200ms)
        result = self.llm_classifier.classify(operation)
        return result
```

**Layer 1: Heuristic Classifier**
```python
class HeuristicClassifier:
    """Fast pattern matching."""
    
    def __init__(self, patterns: List[Pattern]):
        # Compile regex patterns
        self.patterns = [
            (re.compile(p.regex), p.tier, p.tags)
            for p in patterns
        ]
    
    def classify(self, operation: DataOperation) -> Classification:
        # Check file path
        for regex, tier, tags in self.patterns:
            if regex.match(operation.resource_id):
                return Classification(
                    tier=tier,
                    confidence=1.0,
                    tags=tags,
                    reasoning=f"Matched pattern: {regex.pattern}"
                )
        
        # Check for known PII columns
        if operation.resource_type == "table":
            columns = get_table_columns(operation.resource_id)
            pii_columns = [c for c in columns if self.is_pii_column(c)]
            
            if pii_columns:
                return Classification(
                    tier=Tier.PROPRIETARY,
                    confidence=1.0,
                    tags=["PII"],
                    reasoning=f"Contains PII columns: {pii_columns}"
                )
        
        # No match
        return Classification(tier=None, confidence=0.0)
```

**Layer 2: Embedding Classifier**
```python
class EmbeddingClassifier:
    """Semantic similarity matching."""
    
    def __init__(self, model_name: str, examples: Dict[Tier, List[str]]):
        self.model = SentenceTransformer(model_name)
        
        # Pre-compute embeddings for examples
        self.example_embeddings = {}
        for tier, texts in examples.items():
            embeddings = self.model.encode(texts)
            self.example_embeddings[tier] = embeddings
    
    def classify(self, operation: DataOperation) -> Classification:
        # Create description of operation
        description = self.describe_operation(operation)
        
        # Compute embedding
        query_embedding = self.model.encode([description])[0]
        
        # Find most similar example
        best_tier = None
        best_similarity = 0.0
        
        for tier, examples in self.example_embeddings.items():
            similarities = cosine_similarity([query_embedding], examples)[0]
            max_sim = max(similarities)
            
            if max_sim > best_similarity:
                best_similarity = max_sim
                best_tier = tier
        
        return Classification(
            tier=best_tier,
            confidence=best_similarity,
            reasoning=f"Semantic similarity: {best_similarity:.2f}"
        )
```

**Layer 3: LLM Classifier**
```python
class LLMClassifier:
    """LLM-based reasoning for complex cases."""
    
    def classify(self, operation: DataOperation) -> Classification:
        # Build context
        context = self.build_context(operation)
        
        # Construct prompt
        prompt = f"""
        Classify this data operation:
        
        Action: {operation.action}
        Resource: {operation.resource_id}
        User: {operation.user.role}
        Context: {context}
        
        Classification tiers:
        - PROPRIETARY: Competitive secrets, PII, regulated data
        - INTERNAL: Internal use only, not competitive
        - PUBLIC: Publicly available or could be
        
        Respond with JSON:
        {{
          "tier": "PROPRIETARY" | "INTERNAL" | "PUBLIC",
          "confidence": 0.0-1.0,
          "reasoning": "explanation",
          "tags": ["tag1", "tag2"]
        }}
        """
        
        # Call LLM
        response = self.llm.chat([
            {"role": "user", "content": prompt}
        ])
        
        # Parse response
        result = json.loads(response.content)
        
        return Classification(
            tier=Tier[result["tier"]],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            tags=result["tags"]
        )
```

### 3. Lineage Tracker

**Purpose**: Build complete data lineage graph

```python
class LineageTracker:
    """Track data lineage across operations."""
    
    def __init__(self):
        self.graph = nx.DiGraph()  # NetworkX directed graph
    
    def track_operation(self, operation: DataOperation):
        """Record operation in lineage graph."""
        
        # Add nodes
        for source in operation.sources:
            if source not in self.graph:
                self.graph.add_node(source, **self.get_metadata(source))
        
        self.graph.add_node(
            operation.destination,
            **self.get_metadata(operation.destination)
        )
        
        # Add edges (sources → destination)
        for source in operation.sources:
            self.graph.add_edge(
                source,
                operation.destination,
                operation=operation.action,
                timestamp=datetime.now(),
                user=operation.user.id,
                code=operation.code  # Transformation code if available
            )
    
    def get_upstream(self, resource: str) -> List[str]:
        """Get all upstream dependencies."""
        return list(nx.ancestors(self.graph, resource))
    
    def get_downstream(self, resource: str) -> List[str]:
        """Get all downstream dependencies."""
        return list(nx.descendants(self.graph, resource))
    
    def get_lineage_chain(self, resource: str) -> List[str]:
        """Get full lineage path."""
        # Find all paths to root nodes (sources with no parents)
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        
        chains = []
        for root in roots:
            try:
                path = nx.shortest_path(self.graph, root, resource)
                chains.append(path)
            except nx.NetworkXNoPath:
                continue
        
        return chains
```

**Classification Inheritance**
```python
class ClassificationInheritance:
    """Apply inheritance rules to derived data."""
    
    def infer_classification(
        self,
        operation: DataOperation,
        source_classifications: List[Classification]
    ) -> Classification:
        """Infer classification for operation result."""
        
        if operation.action == "join":
            # Maximum classification of sources
            max_tier = max(c.tier for c in source_classifications)
            union_tags = set()
            for c in source_classifications:
                union_tags.update(c.tags)
            
            return Classification(
                tier=max_tier,
                tags=list(union_tags),
                reasoning="Inherited maximum classification from join sources"
            )
        
        elif operation.action == "aggregate":
            # May downgrade if no individual-level data
            if self.preserves_individual_data(operation):
                # Group-by with low cardinality → individuals still identifiable
                return max(source_classifications, key=lambda c: c.tier)
            else:
                # High cardinality aggregation → safe to downgrade
                max_tier = max(c.tier for c in source_classifications)
                downgraded = self.downgrade_tier(max_tier)
                
                return Classification(
                    tier=downgraded,
                    tags=["DERIVED_FROM_" + max_tier.name],
                    reasoning="Downgraded due to aggregation without individual data"
                )
        
        elif operation.action == "filter":
            # Inherit source classification
            return source_classifications[0]
        
        elif operation.action == "anonymize":
            # Downgrade to INTERNAL if anonymization verified
            if self.verify_anonymization(operation):
                return Classification(
                    tier=Tier.INTERNAL,
                    tags=["ANONYMIZED"],
                    reasoning="Anonymization verified, downgraded from PROPRIETARY"
                )
            else:
                # Keep original classification if anonymization insufficient
                return source_classifications[0]
        
        else:
            # Default: inherit maximum classification
            return max(source_classifications, key=lambda c: c.tier)
```

### 4. Policy Engine (OPA)

**Integration with Open Policy Agent:**

```python
class OPAPolicyEngine:
    """Evaluate policies using OPA."""
    
    def __init__(self, opa_url: str):
        self.opa_url = opa_url
    
    def evaluate(
        self,
        operation: DataOperation,
        classification: Classification
    ) -> PolicyDecision:
        """Evaluate operation against policies."""
        
        # Build OPA input
        input_data = {
            "action": operation.action,
            "source": {
                "classification": classification.tier.value,
                "tags": classification.tags,
                "lineage": operation.lineage_chain
            },
            "destination": {
                "type": operation.destination_type,
                "path": operation.destination,
                "encrypted": operation.destination_encrypted
            },
            "user": {
                "id": operation.user.id,
                "role": operation.user.role,
                "clearance": operation.user.clearance,
                "department": operation.user.department
            },
            "context": {
                "purpose": operation.purpose,
                "environment": os.getenv("ENVIRONMENT", "production")
            }
        }
        
        # Query OPA
        response = requests.post(
            f"{self.opa_url}/v1/data/governance/allow",
            json={"input": input_data},
            timeout=0.1  # 100ms timeout
        )
        
        result = response.json()["result"]
        
        return PolicyDecision(
            allowed=result.get("allow", False),
            policy_id=result.get("policy_id"),
            policy_version=result.get("policy_version"),
            reasoning=result.get("reasoning", ""),
            alternatives=result.get("alternatives", [])
        )
```

**Example OPA Policy:**
```rego
package governance

# Allow export if all conditions met
allow {
    # Not PROPRIETARY data
    input.source.classification != "PROPRIETARY"
}

allow {
    # Or destination is approved
    approved_destination
}

allow {
    # Or exception granted
    input.exception.approved == true
}

# Helper: Check approved destinations
approved_destination {
    input.destination.type == "governed_storage"
    input.destination.encrypted == true
}

approved_destination {
    input.destination.type == "database"
    startswith(input.destination.path, "/approved/")
}

# Provide alternatives when denied
alternatives[msg] {
    not allow
    input.source.tags[_] == "PII"
    msg := "Anonymize PII: lacuna.anonymize(data, pii_columns)"
}

alternatives[msg] {
    not allow
    msg := sprintf("Save to governed storage: %v", [approved_paths[0]])
}

# List of approved paths
approved_paths := [
    "/governed/workspace/",
    "s3://company-governed-data/"
]
```

### 5. Audit Logger

**Tamper-Evident Logging with Hash Chains:**

```python
class AuditLogger:
    """ISO 27001-compliant audit logging."""
    
    def __init__(self, backend: AuditBackend):
        self.backend = backend
        self.queue = Queue()  # Async logging
        
        # Start background writer
        self.writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True
        )
        self.writer_thread.start()
    
    def log(self, event: AuditEvent):
        """Log audit event (non-blocking)."""
        
        # Create audit record
        record = AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp=self.get_ntp_time(),
            event_type=event.type,
            severity=event.severity,
            user_id=event.user.id,
            resource_id=event.resource_id,
            action=event.action,
            action_result=event.result,
            # ... full record fields
        )
        
        # Queue for async write
        self.queue.put(record)
    
    def _writer_loop(self):
        """Background thread that writes batches."""
        batch = []
        
        while True:
            try:
                # Collect batch
                while len(batch) < 100:
                    record = self.queue.get(timeout=1.0)
                    batch.append(record)
            except Empty:
                pass  # Timeout, write what we have
            
            # Write batch
            if batch:
                self._write_batch(batch)
                batch = []
    
    def _write_batch(self, records: List[AuditRecord]):
        """Write batch with hash chain."""
        
        # Get last record hash
        last_hash = self.backend.get_last_hash()
        
        # Link records in batch
        for i, record in enumerate(records):
            if i == 0:
                record.previous_record_hash = last_hash
            else:
                record.previous_record_hash = records[i-1].record_hash
            
            # Compute this record's hash
            record.record_hash = self._compute_hash(record)
            last_hash = record.record_hash
        
        # Write batch atomically
        self.backend.write_batch(records)
```

**Hash Computation:**
```python
def _compute_hash(self, record: AuditRecord) -> str:
    """Compute SHA-256 hash of record."""
    
    # Serialize record deterministically
    data = {
        "event_id": record.event_id,
        "timestamp": record.timestamp.isoformat(),
        "event_type": record.event_type.value,
        "user_id": record.user_id,
        "resource_id": record.resource_id,
        "action": record.action,
        "action_result": record.action_result,
        "previous_record_hash": record.previous_record_hash,
        # Include all relevant fields...
    }
    
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()
```

## Data Flow Example

**Scenario: User exports customer data**

```
1. User Code:
   customers.to_csv("~/Downloads/export.csv")
   
2. Operation Interceptor (IPython magic):
   ├─ Detects: file write operation
   ├─ Creates DataOperation object
   └─ Passes to Classification Pipeline
   
3. Classification Pipeline:
   ├─ Layer 1 (Heuristics):
   │  ├─ Checks file path patterns → no match
   │  └─ Checks DataFrame columns → finds "email", "phone"
   │  └─ Returns: PROPRIETARY (confidence: 1.0)
   │
   └─ [Layers 2, 3 skipped due to high confidence]
   
4. Lineage Tracker:
   ├─ Traces: customers.csv → customers DataFrame → export.csv
   ├─ Inherits classification: export.csv = PROPRIETARY
   └─ Tags: [PII, CUSTOMER_DATA, EMAIL, PHONE]
   
5. Policy Engine (OPA):
   ├─ Query: Can user export PROPRIETARY to ~/Downloads?
   ├─ Policy evaluation:
   │  ├─ Check: classification != PROPRIETARY → FALSE
   │  ├─ Check: destination approved → FALSE
   │  └─ Check: exception granted → FALSE
   │
   └─ Decision: DENY
      └─ Alternatives:
         • "Anonymize: lacuna.anonymize(customers, ['email', 'phone'])"
         • "Save to: /governed/workspace/export.csv"
         
6. Audit Logger:
   ├─ Create audit record:
   │  ├─ event_type: DATA_EXPORT
   │  ├─ action_result: denied
   │  ├─ reasoning: "Cannot export PROPRIETARY to unmanaged location"
   │  └─ previous_record_hash: <hash of last record>
   │
   ├─ Compute hash chain:
   │  └─ record_hash: SHA256(record + previous_hash)
   │
   └─ Write to PostgreSQL (async)
   
7. User Feedback:
   Display inline error with alternatives
   
8. Alerting (if configured):
   ├─ Check alert rules
   ├─ Match: "proprietary_data_export"
   └─ Notify: #data-governance on Slack
```

## Performance Characteristics

### Latency Targets

| Component | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Heuristic Classification | <1ms | 0.5ms | Regex matching |
| Embedding Classification | <10ms | 5ms | Cached embeddings |
| LLM Classification | <200ms | 150ms | Rare (2% of ops) |
| Policy Evaluation (OPA) | <50ms | 20ms | Cached policies |
| Audit Logging | Non-blocking | 0ms (async) | Queued writes |
| **Total (98% of ops)** | **<50ms** | **25ms** | Heuristic + policy |
| **Total (2% of ops)** | **<300ms** | **190ms** | LLM + policy |

### Throughput Targets

| Operation | Target | Scalability |
|-----------|--------|-------------|
| Classifications/second | 1,000+ | Horizontal scaling |
| Policy evaluations/second | 5,000+ | OPA sidecars |
| Audit log writes/second | 10,000+ | Batching + async |

## Deployment Architecture

### Single-Tenant Deployment

```
┌──────────────────────────────────────────────────┐
│                Load Balancer                     │
└────────────┬─────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼───┐
│ Lacuna │      │ Lacuna │  (Multiple instances)
│ Core   │      │ Core   │
└───┬────┘      └────┬───┘
    │                │
    └────────┬───────┘
             │
    ┌────────▼────────┐
    │  PostgreSQL     │ (Audit logs)
    │  Cluster        │
    └─────────────────┘
    
    ┌─────────────────┐
    │  OPA Server     │ (Policy engine)
    └─────────────────┘
    
    ┌─────────────────┐
    │  Redis Cache    │ (Classifications, embeddings)
    └─────────────────┘
```

### Multi-Tenant Deployment

```
┌──────────────────────────────────────────────────┐
│           API Gateway + Tenant Router            │
└────────┬─────────────────────────────────────────┘
         │
    ┌────┴─────────────────┐
    │                      │
┌───▼──────┐        ┌─────▼────┐
│ Tenant A │        │ Tenant B │
│ Namespace│        │ Namespace│
└───┬──────┘        └─────┬────┘
    │                     │
┌───▼──────────────────────▼────┐
│     Shared PostgreSQL         │
│     (Row-level security)      │
└───────────────────────────────┘

┌────────────────────────────────┐
│     Shared OPA Server          │
│     (Per-tenant policies)      │
└────────────────────────────────┘
```

## Summary

Lacuna's architecture provides:

✓ **Modular design** - Components can be deployed/scaled independently
✓ **Performance** - 98% of operations complete in <50ms
✓ **Scalability** - Horizontal scaling for all components
✓ **Extensibility** - Pluggable classifiers, policies, integrations
✓ **Reliability** - Async logging, graceful degradation
✓ **Compliance** - Tamper-evident audit logs, complete provenance

