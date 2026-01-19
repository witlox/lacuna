# Plugin Ecosystem

**Lacuna** - The protected space where your knowledge stays yours

Lacuna is designed with a **plugin-first architecture** that enables organizations to integrate existing classification systems while remaining lightweight and usable for individual users.

## Philosophy: Enterprise-First, Individual-Friendly

### Core Design Principle

**Plugins are optional enhancements, not requirements.**

- **Without plugins**: Three-layer classification (heuristic, embedding, LLM) works standalone
- **With plugins**: Enhanced accuracy, compliance integration, domain expertise

### Target Audiences

**Individual Users** (recommended: `plugins-individual`)
- Local PII detection (Presidio)
- Few-shot learning (SetFit)
- No enterprise dependencies
- Quick setup, immediate value

**Enterprise Users** (recommended: `plugins-enterprise`)
- All individual plugins
- Policy-as-code (OPA)
- Compliance logging
- Multi-user support

**Domain-Specific** (healthcare, finance, legal)
- Industry-specific classifiers
- Regulatory compliance (HIPAA, PCI-DSS, SOX)
- Domain terminology detection

## Available Plugins

### Individual User Plugins (`plugins-individual`)

#### 1. Presidio PII Detection

**What it does**: Detects Personally Identifiable Information using ML models

**Why use it**: Catches PII that simple regex misses (phone numbers in various formats, names, locations)

**Installation**:
```bash
pip install lacuna[plugins-individual]
```

**Usage**:
```python
from lacuna.plugins import PresidioPlugin

presidio = PresidioPlugin(
    entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "SSN"],
    priority=5
)
pipeline.register(presidio)
```

**Features**:
- 50+ built-in PII recognizers
- Multi-language support (15+ languages)
- Custom recognizer support
- Runs entirely locally (no API calls)
- 85-95% accuracy on common PII

**Performance**:
- Latency: 5-20ms per query
- Memory: ~500MB (models loaded)
- CPU-based (no GPU required)

**Example detections**:
```python
"Call me at 555-123-4567" → PHONE_NUMBER detected → PROPRIETARY
"My email is john@example.com" → EMAIL_ADDRESS → PROPRIETARY
"SSN: 123-45-6789" → SSN detected → PROPRIETARY
```

**Custom recognizers**:
```yaml
# config/plugins.yaml
presidio:
  custom_recognizers:
    - name: EMPLOYEE_ID
      pattern: "EMP-\\d{6}"
      score: 0.9
```

#### 2. SetFit Few-Shot Classification

**What it does**: Learns your organization's classification patterns with minimal examples

**Why use it**: Better than cosine similarity, improves with user corrections

**Installation**:
```bash
pip install lacuna[plugins-individual]
```

**Usage**:
```python
from lacuna.plugins import SetFitPlugin

# Train from examples
setfit = SetFitPlugin(
    examples={
        Tier.PROPRIETARY: [
            "How do we optimize our auth system?",
            "Debug project_apollo error",
            # 8-16 examples
        ],
        Tier.PUBLIC: [
            "Latest Python version?",
            "How does MVCC work?",
            # 8-16 examples
        ],
    },
    priority=20
)

# Or load pre-trained
setfit = SetFitPlugin.from_pretrained("./models/classifier")
pipeline.register(setfit)
```

**Features**:
- Few-shot learning (8-16 examples per tier)
- Automatic retraining on user corrections
- Fast inference (5-10ms)
- 85-92% accuracy after initial training

**Training workflow**:
```
1. Start with 8-16 examples per tier
2. System classifies queries
3. User corrects misclassifications
4. After 50 corrections, auto-retrain
5. Accuracy improves to 90%+
```

**Performance**:
- Training: ~2 minutes (one-time)
- Inference: 5-10ms per query
- Memory: ~200MB (model loaded)
- GPU optional (CPU works fine)

### Enterprise Plugins (`plugins-enterprise`)

#### 3. Open Policy Agent (OPA)

**What it does**: Policy-as-code for compliance-driven classification

**Why use it**: Separates policy (compliance team) from implementation (engineering)

**Installation**:
```bash
pip install lacuna[plugins-enterprise]
```

**Setup**:
```bash
# Start OPA server
docker run -p 8181:8181 -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest run --server --addr :8181 /policies
```

**Usage**:
```python
from lacuna.plugins import OPAPlugin

opa = OPAPlugin(
    endpoint="http://localhost:8181",
    policy_path="privacy/classify",
    priority=10
)
pipeline.register(opa)
```

**Policy example** (`policies/privacy.rego`):
```rego
package privacy

# Rule: Customer references are always PROPRIETARY
classify[{
    "tier": "PROPRIETARY",
    "confidence": 1.0,
    "reason": "Customer data reference"
}] {
    contains(lower(input.query), "customer")
}

# Rule: Public technology questions
classify[{
    "tier": "PUBLIC",
    "confidence": 0.9,
    "reason": "General technical question"
}] {
    startswith(lower(input.query), "what is")
}

# Rule: Project-specific (from context)
classify[{
    "tier": "PROPRIETARY",
    "confidence": 1.0,
    "reason": "Project context indicates proprietary"
}] {
    input.context.project != null
    input.context.project != "learning"
}
```

**Features**:
- Declarative policy language (Rego)
- Version-controlled policies
- Centralized policy management
- Audit trail built-in
- Policy testing framework

**Use cases**:
- SOX compliance (financial data protection)
- GDPR compliance (EU data residency)
- ITAR compliance (defense/export control)
- Custom organizational policies

**Performance**:
- Latency: <5ms (local OPA server)
- Scales to thousands of rules
- Policy evaluation cached

#### 4. Microsoft Purview (Enterprise Only)

**What it does**: Integrates with existing Microsoft Purview classification

**Why use it**: Organizations already using Purview have trained models and defined labels

**⚠️ Privacy Warning**: **Only use with on-premises or private cloud deployment**

**Installation**:
```bash
pip install lacuna[cloud-azure]
```

**Usage**:
```python
from lacuna.plugins import PurviewPlugin

# Requires private deployment
purview = PurviewPlugin(
    endpoint="https://your-purview.purview.azure.com",
    credential=credential,
    priority=15
)
pipeline.register(purview)
```

**Label mapping**:
```yaml
# Map Purview labels to our tiers
label_mapping:
  "Highly Confidential": PROPRIETARY
  "Confidential": PROPRIETARY
  "Internal Use Only": INTERNAL
  "Public": PUBLIC
```

**Requirements**:
- Purview deployed on-premises or private cloud
- Do NOT send to public Azure (defeats privacy goal)
- Enterprise licensing required

#### 5. Google Cloud DLP (Enterprise Only)

**What it does**: Advanced PII and sensitive data detection

**Why use it**: 120+ built-in detectors, custom info types

**⚠️ Privacy Warning**: **Only use with on-premises deployment**

**Installation**:
```bash
pip install lacuna[cloud-gcp]
```

**Usage**:
```python
from lacuna.plugins import GoogleDLPPlugin

# Requires on-prem or private GCP
dlp = GoogleDLPPlugin(
    project_id="your-project",
    location="us",  # or on-prem location
    priority=15
)
pipeline.register(dlp)
```

**Features**:
- 120+ built-in info types
- Custom info type detection
- Risk scoring
- De-identification capabilities

**Requirements**:
- Sensitive Data Protection on-prem
- Do NOT send to public GCP APIs
- Enterprise licensing

### Domain-Specific Plugins

#### 6. Healthcare Plugin (`plugins-healthcare`)

**What it does**: Medical NER and PHI detection for HIPAA compliance

**Why use it**: Healthcare organizations need PHI protection

**Installation**:
```bash
pip install lacuna[plugins-healthcare]

# Download medical NER model
python -m spacy download en_core_sci_md
```

**Usage**:
```python
from lacuna.plugins import HealthcarePlugin

healthcare = HealthcarePlugin(
    models=["en_core_sci_md"],
    detect_phi=True,
    priority=5
)
pipeline.register(healthcare)
```

**Detects**:
- Medical conditions (diabetes, hypertension)
- Symptoms (fever, pain)
- Medications (aspirin, metformin)
- Procedures (surgery, biopsy)
- Lab values (blood pressure, glucose)
- PHI (patient identifiers)

**HIPAA compliance**:
- Detects 18 HIPAA identifiers
- Labels PHI as PROPRIETARY
- Prevents external queries with PHI

**Example**:
```python
"Patient's blood pressure is 140/90" 
→ Medical entities detected 
→ PROPRIETARY 
→ Local RAG only
```

#### 7. Finance Plugin (`plugins-finance`)

**What it does**: Financial data and PCI-DSS compliance

**Installation**:
```bash
pip install lacuna[plugins-finance]
```

**Usage**:
```python
from lacuna.plugins import FinancePlugin

finance = FinancePlugin(
    detect_pci=True,
    detect_securities=True,
    priority=5
)
pipeline.register(finance)
```

**Detects**:
- Credit card numbers (PCI-DSS)
- Bank account numbers
- Routing numbers
- Securities (stock symbols, CUSIP, ISIN)
- Financial identifiers

**Compliance**:
- PCI-DSS Level 1 compliant
- SOX compliance support
- Audit logging

## Plugin Configuration

### Configuration File

```yaml
# config/plugins.yaml

plugins:
  # Enable/disable and configure each plugin
  presidio:
    enabled: true
    priority: 5
    entities: [PHONE_NUMBER, EMAIL_ADDRESS, CREDIT_CARD]
  
  setfit:
    enabled: true
    priority: 20
    model_path: ./models/setfit-classifier
    auto_train: true
  
  opa:
    enabled: false  # Enterprise only
    priority: 10
    endpoint: http://localhost:8181

# Pipeline behavior
behavior:
  short_circuit: true  # Stop at first high-confidence result
  confidence_threshold: 0.90
  fail_safe: true  # Continue on plugin errors
```

### Loading Plugins

```python
from lacuna.config import load_plugin_config

# Load configuration
config = load_plugin_config("config/plugins.yaml")

# Auto-register enabled plugins
pipeline.register_from_config(config)
```

## Creating Custom Plugins

### Plugin Interface

```python
from lacuna.classifier import ClassifierPlugin
from lacuna.models import Classification, Tier
from typing import Optional

class MyCustomPlugin(ClassifierPlugin):
    """Custom plugin for organization-specific rules."""
    
    # Priority (1-100, lower = earlier)
    priority = 10
    
    def __init__(self, custom_config: dict):
        """Initialize with custom configuration."""
        self.config = custom_config
    
    def classify(
        self, 
        query: str, 
        context: dict
    ) -> Optional[Classification]:
        """
        Classify query or return None.
        
        Args:
            query: User's query text
            context: Conversation history, files, project
            
        Returns:
            Classification if applicable, None otherwise
        """
        # Your classification logic
        if self.is_sensitive(query):
            return Classification(
                tier=Tier.PROPRIETARY,
                confidence=0.95,
                reasoning="Custom rule: sensitive term detected",
                metadata={"plugin": self.name, "rule": "custom_001"}
            )
        
        # Not applicable, pass to next plugin
        return None
    
    @property
    def name(self) -> str:
        """Plugin name for logging."""
        return "MyCustomPlugin"
```

### Plugin Best Practices

1. **Return None when uncertain**: Let other plugins handle it
2. **High confidence for clear matches**: 0.90+ when you're sure
3. **Include reasoning**: Explain why classification was chosen
4. **Handle errors gracefully**: Don't crash the pipeline
5. **Document priority**: Explain when plugin should run
6. **Add comprehensive tests**: Test edge cases

### Plugin Testing

```python
import pytest
from lacuna.plugins import MyCustomPlugin

class TestMyCustomPlugin:
    @pytest.fixture
    def plugin(self):
        return MyCustomPlugin(config={})
    
    def test_detects_sensitive_term(self, plugin):
        """Should detect proprietary term."""
        query = "How do we handle acme_corp data?"
        result = plugin.classify(query, context={})
        
        assert result is not None
        assert result.tier == Tier.PROPRIETARY
        assert result.confidence > 0.90
    
    def test_ignores_public_query(self, plugin):
        """Should return None for public queries."""
        query = "What's the latest Python version?"
        result = plugin.classify(query, context={})
        
        assert result is None  # Pass to next plugin
```

## Plugin Execution Flow

```
User Query
    ↓
┌─────────────────────────────────────┐
│ PluggableClassificationPipeline     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Run plugins in priority order       │
│ (1 → 100)                           │
└─────────────────────────────────────┘
    ↓
For each plugin:
    ├─ Call plugin.classify(query, context)
    ├─ If result and confidence >= 0.90:
    │   └─ Return result (short-circuit)
    └─ If result but confidence < 0.90:
        └─ Add to results list
    ↓
If no short-circuit:
    ├─ Aggregate results
    └─ Return highest confidence
    ↓
If no plugins returned results:
    └─ Use default pipeline (heuristic → embedding → LLM)
```

## Plugin Priority Guidelines

```
Priority 1-10: Critical Security/Compliance
├─ 5: PII detection (Presidio, Healthcare, Finance)
├─ 8: Policy enforcement (OPA)
└─ 10: Enterprise classification (Purview, DLP)

Priority 11-50: ML-Based Classification
├─ 15: Cloud services (if on-prem)
├─ 20: SetFit (few-shot learning)
└─ 30: Zero-shot classifiers

Priority 51-100: Core Pipeline (Fallback)
├─ 60: Heuristic rules
├─ 70: Embedding similarity
└─ 80: LLM classification
```

## Performance Impact

### With No Plugins (Baseline)

```
Query → Heuristic (1ms) → Embedding (10ms) → LLM (200ms)
Average: 15ms (90% heuristic, 8% embedding, 2% LLM)
```

### With Individual Plugins

```
Query → Presidio (15ms) → SetFit (8ms) → Heuristic (1ms)
Average: 18ms (3ms overhead for enhanced accuracy)
```

### With Enterprise Plugins

```
Query → OPA (3ms) → Presidio (15ms) → SetFit (8ms) → Heuristic (1ms)
Average: 21ms (6ms overhead for policy + PII + ML)
```

**Recommendation**: Plugin overhead is negligible (<10ms) for the accuracy improvement.

## Plugin Ecosystem Roadmap

### Current State (v0.1)

- [x] Plugin architecture defined
- [x] Presidio integration (PII detection)
- [x] SetFit integration (few-shot learning)
- [ ] OPA integration (policy-as-code)
- [ ] Healthcare plugin
- [ ] Finance plugin

### Near-term (v0.2-0.3)

- [ ] Plugin marketplace/registry
- [ ] Community-contributed plugins
- [ ] Plugin templates and generator
- [ ] Plugin performance benchmarks
- [ ] Plugin compatibility matrix

### Long-term (v1.0+)

- [ ] Federated learning plugins
- [ ] Cross-organization plugin sharing
- [ ] Plugin versioning and dependencies
- [ ] Plugin sandboxing/isolation
- [ ] Plugin hot-reload

## Getting Help

- **Plugin issues**: GitHub Issues with `[Plugin]` tag
- **Custom plugin development**: See `CONTRIBUTING.md`
- **Enterprise setup**: Email enterprise@lacuna.dev
- **Plugin requests**: GitHub Discussions

## Contributing Plugins

We welcome community-contributed plugins! See:
- `CONTRIBUTING.md` for general guidelines
- `docs/PLUGIN_DEVELOPMENT.md` for detailed plugin creation guide
- `examples/custom_plugin/` for working examples

Popular plugin categories we're looking for:
- Legal (contract analysis, regulatory compliance)
- Scientific (research data protection)
- Government (classified information handling)
- Education (FERPA compliance)
