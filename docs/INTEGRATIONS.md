# Framework Integrations

**Lacuna** - The protected space where your knowledge stays yours

Integrate Lacuna's privacy-aware routing with popular RAG frameworks and vector databases.

---

## Overview

Lacuna integrates with existing RAG frameworks as a **privacy layer**, adding sensitivity-aware routing without replacing your current stack.

```
┌─────────────────────────────────────────────────────────┐
│                    Your RAG Application                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LlamaIndex / LangChain → Lacuna Router → Sources       │
│         ↓                       ↓              ↓        │
│    Query Engine          Classification   Local/Web     │
│                               ↓                         │
│                    ┌──────────────────────┐             │
│                    │  Lacuna Classifier   │             │
│                    │  - Heuristics        │             │
│                    │  - Embeddings        │             │
│                    │  - LLM               │             │
│                    │  - Plugins (OPA)     │             │
│                    └──────────────────────┘             │
│                               ↓                         │
│              ┌────────────────┴────────────────┐        │
│              ↓                                 ↓        │
│    ┌──────────────────┐              ┌──────────────┐   │
│    │   Local Sources  │              │ Web Sources  │   │
│    │  - Qdrant        │              │  - Kagi API  │   │
│    │  - ChromaDB      │              │  - Brave API │   │
│    │  - Weaviate      │              │              │   │
│    └──────────────────┘              └──────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## LlamaIndex Integration

### Installation

```bash
# Install Lacuna with LlamaIndex support
pip install lacuna[llamaindex]

# Or separately
pip install lacuna llama-index
```

### Basic Integration

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.query_engine import RouterQueryEngine
from lacuna.integrations.llamaindex import PrivacyAwareRouter

# 1. Load documents
documents = SimpleDirectoryReader("./data").load_data()

# 2. Create local index
local_index = VectorStoreIndex.from_documents(documents)

# 3. Initialize Lacuna router
lacuna_router = PrivacyAwareRouter(
    config_path="config/",
    local_index=local_index,
    web_search_enabled=True,
    web_search_provider="kagi"  # or "brave", "duckduckgo"
)

# 4. Query with automatic privacy routing
response = lacuna_router.query(
    "How do we handle authentication in project_apollo?"
)
# → Classified as PROPRIETARY → Routes to local_index only

response = lacuna_router.query(
    "What's the latest Python 3.12 features?"
)
# → Classified as PUBLIC → Routes to local_index + web search
```

### Advanced: Custom Query Engines

```python
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import SubQuestionQueryEngine
from lacuna.integrations.llamaindex import PrivacyAwareQueryEngine

# Multiple local indices
proprietary_index = VectorStoreIndex.from_documents(proprietary_docs)
internal_index = VectorStoreIndex.from_documents(internal_docs)

# Wrap with Lacuna privacy routing
query_engine = PrivacyAwareQueryEngine(
    proprietary_engine=proprietary_index.as_query_engine(),
    internal_engine=internal_index.as_query_engine(),
    public_engine=None,  # Use web search for public
    classifier_config="config/",
    routing_strategy="conservative"
)

# Automatic routing based on classification
response = query_engine.query("User query here")
```

### Sub-Question Decomposition with Privacy

```python
from llama_index.core.tools import QueryEngineTool
from llama_index.core.query_engine import SubQuestionQueryEngine
from lacuna.integrations.llamaindex import PrivacyAwareSubQuestionEngine

# Define tools (each with privacy tier)
proprietary_tool = QueryEngineTool.from_defaults(
    query_engine=proprietary_index.as_query_engine(),
    name="proprietary_docs",
    description="Company proprietary documentation",
    privacy_tier="PROPRIETARY"  # Lacuna extension
)

public_tool = QueryEngineTool.from_defaults(
    query_engine=web_search_engine,
    name="web_search",
    description="Public web search",
    privacy_tier="PUBLIC"
)

# Privacy-aware sub-question engine
sub_question_engine = PrivacyAwareSubQuestionEngine.from_tools(
    [proprietary_tool, public_tool],
    classifier_config="config/"
)

# Complex query decomposed with privacy awareness
response = sub_question_engine.query(
    "Compare our ML pipeline to industry best practices"
)
# → Sub-question 1: "Our ML pipeline" → PROPRIETARY → proprietary_docs
# → Sub-question 2: "Industry best practices" → PUBLIC → web_search
```

### Streaming Responses

```python
from lacuna.integrations.llamaindex import PrivacyAwareStreamingEngine

streaming_engine = PrivacyAwareStreamingEngine(
    local_index=local_index,
    web_search_enabled=True
)

# Stream response with privacy check upfront
for chunk in streaming_engine.stream_query("Your query"):
    print(chunk, end="", flush=True)
```

---

## LangChain Integration

### Installation

```bash
# Install Lacuna with LangChain support
pip install lacuna[langchain]

# Or separately
pip install lacuna langchain langchain-community
```

### Basic Integration

```python
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from lacuna.integrations.langchain import PrivacyAwareRetriever

# 1. Create local vector store
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
local_vectorstore = Qdrant.from_documents(
    documents,
    embeddings,
    location=":memory:"
)

# 2. Wrap with Lacuna privacy-aware retriever
lacuna_retriever = PrivacyAwareRetriever(
    local_retriever=local_vectorstore.as_retriever(),
    web_search_enabled=True,
    config_path="config/"
)

# 3. Create QA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=local_llm,
    retriever=lacuna_retriever,
    return_source_documents=True
)

# 4. Query with automatic privacy routing
result = qa_chain({"query": "How do we deploy to production?"})
```

### Multi-Retriever with Privacy Tiers

```python
from langchain.retrievers import EnsembleRetriever
from lacuna.integrations.langchain import TieredRetriever

# Different retrievers for different tiers
proprietary_retriever = qdrant_proprietary.as_retriever()
internal_retriever = qdrant_internal.as_retriever()
web_retriever = web_search_tool.as_retriever()

# Lacuna routes to appropriate retriever(s)
tiered_retriever = TieredRetriever(
    retrievers={
        "PROPRIETARY": proprietary_retriever,
        "INTERNAL": internal_retriever,
        "PUBLIC": web_retriever
    },
    classifier_config="config/"
)

# Automatic tier-based routing
docs = tiered_retriever.get_relevant_documents(
    "What's our customer retention strategy?"
)
# → PROPRIETARY → Uses only proprietary_retriever
```

### Conversational RAG with Memory

```python
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from lacuna.integrations.langchain import PrivacyAwareConversationalChain

# Memory for conversation history
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="answer"
)

# Privacy-aware conversational chain
conv_chain = PrivacyAwareConversationalChain.from_llm(
    llm=local_llm,
    retriever=lacuna_retriever,
    memory=memory,
    classifier_config="config/"
)

# Context-aware classification (considers conversation history)
response = conv_chain({"question": "Tell me more about that"})
# → Classification considers previous messages for context
```

### LangGraph Agent with Privacy

```python
from langgraph.prebuilt import create_react_agent
from lacuna.integrations.langchain import privacy_aware_tools

# Tools with privacy annotations
tools = privacy_aware_tools([
    {
        "name": "search_proprietary",
        "func": lambda q: search_qdrant(q),
        "description": "Search proprietary documents",
        "privacy_tier": "PROPRIETARY"
    },
    {
        "name": "search_web",
        "func": lambda q: search_kagi(q),
        "description": "Search public web",
        "privacy_tier": "PUBLIC"
    }
])

# Agent with Lacuna privacy checks
agent = create_react_agent(
    model=local_llm,
    tools=tools,
    checkpointer=memory_checkpointer
)

# Lacuna validates tool selection matches query sensitivity
for chunk in agent.stream(
    {"messages": [("user", "How do we optimize ML pipeline?")]}
):
    print(chunk)
# → Lacuna ensures agent only uses proprietary_search tool
```

---

## Vector Database Integrations

### Qdrant

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from lacuna.integrations.vectordb import PrivacyAwareQdrant

# Initialize Qdrant client
client = QdrantClient(url="http://localhost:6333")

# Create collections with privacy tiers
client.create_collection(
    collection_name="proprietary",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)
client.create_collection(
    collection_name="public",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Wrap with Lacuna
lacuna_qdrant = PrivacyAwareQdrant(
    client=client,
    collections={
        "PROPRIETARY": "proprietary",
        "INTERNAL": "internal",
        "PUBLIC": "public"
    },
    classifier_config="config/"
)

# Query with automatic collection routing
results = lacuna_qdrant.search(
    query="How do we handle customer data?",
    top_k=5
)
# → PROPRIETARY → Searches only "proprietary" collection
```

### ChromaDB

```python
import chromadb
from lacuna.integrations.vectordb import PrivacyAwareChroma

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Create collections
proprietary_collection = chroma_client.create_collection("proprietary")
public_collection = chroma_client.create_collection("public")

# Wrap with Lacuna
lacuna_chroma = PrivacyAwareChroma(
    client=chroma_client,
    collections={
        "PROPRIETARY": proprietary_collection,
        "PUBLIC": public_collection
    },
    classifier_config="config/"
)

# Automatic routing
results = lacuna_chroma.query(
    query_texts=["Customer retention strategies"],
    n_results=10
)
```

### Weaviate

```python
import weaviate
from lacuna.integrations.vectordb import PrivacyAwareWeaviate

# Initialize Weaviate client
weaviate_client = weaviate.Client("http://localhost:8080")

# Create schemas with privacy metadata
weaviate_client.schema.create_class({
    "class": "ProprietaryDocs",
    "properties": [
        {"name": "content", "dataType": ["text"]},
        {"name": "privacy_tier", "dataType": ["string"]}
    ]
})

# Wrap with Lacuna
lacuna_weaviate = PrivacyAwareWeaviate(
    client=weaviate_client,
    classes={
        "PROPRIETARY": "ProprietaryDocs",
        "PUBLIC": "PublicDocs"
    },
    classifier_config="config/"
)

# Query with privacy routing
results = lacuna_weaviate.search(
    query="Latest product roadmap",
    top_k=5
)
```

---

## Web Search Integrations

### Kagi Search API

```python
from lacuna.integrations.search import KagiSearch

# Initialize Kagi search
kagi = KagiSearch(
    api_key="your-kagi-api-key",
    region="us",  # or "eu"
    safe_search=True
)

# Search with privacy classification
results = kagi.search(
    query="Latest Python features",
    max_results=10,
    # Lacuna automatically adds context about query sensitivity
    sensitivity_tier="PUBLIC"
)

# Kagi features
results = kagi.search(
    query="Machine learning best practices",
    summary=True,  # FastGPT summary
    custom_params={
        "freshness": "week"  # Recent results only
    }
)
```

### Brave Search API

```python
from lacuna.integrations.search import BraveSearch

brave = BraveSearch(
    api_key="your-brave-api-key",
    safe_search="strict"
)

results = brave.search(
    query="Rust async programming",
    count=10,
    freshness="pw"  # Past week
)
```

### DuckDuckGo (No API Key)

```python
from lacuna.integrations.search import DuckDuckGoSearch

ddg = DuckDuckGoSearch()

# No API key required
results = ddg.search(
    query="PostgreSQL performance tuning",
    max_results=10,
    region="us-en"
)
```

### SearXNG (Self-Hosted)

```python
from lacuna.integrations.search import SearXNGSearch

searxng = SearXNGSearch(
    instance_url="https://your-searxng.example.com",
    engines=["google", "bing", "duckduckgo"]
)

results = searxng.search(
    query="Kubernetes best practices",
    categories=["general", "it"]
)
```

---

## LLM Backend Integrations

### vLLM (Local)

```python
from lacuna.integrations.llm import VLLMBackend

# Local vLLM server for classification
vllm_backend = VLLMBackend(
    model="meta-llama/Llama-2-70b-chat-hf",
    api_base="http://localhost:8000",
    temperature=0.1  # Low temp for classification
)

# Use in Lacuna classifier
from lacuna.classifier import LLMClassifier

llm_classifier = LLMClassifier(
    backend=vllm_backend,
    system_prompt="You are a privacy classifier..."
)
```

### text-generation-inference (TGI)

```python
from lacuna.integrations.llm import TGIBackend

tgi_backend = TGIBackend(
    endpoint="http://localhost:8080",
    model="mistralai/Mistral-7B-Instruct-v0.2"
)
```

### Ollama (Local)

```python
from lacuna.integrations.llm import OllamaBackend

ollama_backend = OllamaBackend(
    model="llama2:70b",
    base_url="http://localhost:11434"
)
```

### OpenAI-Compatible APIs

```python
from lacuna.integrations.llm import OpenAICompatibleBackend

# Works with OpenRouter, Together, Replicate, etc.
backend = OpenAICompatibleBackend(
    base_url="https://api.together.xyz/v1",
    api_key="your-api-key",
    model="meta-llama/Llama-2-70b-chat-hf"
)
```

---

## Embedding Model Integrations

### Sentence Transformers (Local)

```python
from lacuna.integrations.embeddings import SentenceTransformerEmbeddings

embeddings = SentenceTransformerEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    device="cuda"  # or "cpu"
)

# Use in classifier
from lacuna.classifier import EmbeddingClassifier

classifier = EmbeddingClassifier(
    embeddings=embeddings,
    examples_path="config/classification_examples.yaml"
)
```

### Nomic Embed (Local)

```python
from lacuna.integrations.embeddings import NomicEmbeddings

embeddings = NomicEmbeddings(
    model="nomic-embed-text-v1.5",
    task_type="search_query"
)
```

### OpenAI Embeddings (API)

```python
from lacuna.integrations.embeddings import OpenAIEmbeddings

# Note: Using external API for embeddings
# Consider privacy implications
embeddings = OpenAIEmbeddings(
    api_key="your-api-key",
    model="text-embedding-3-large",
    # Only use for PUBLIC tier queries
    allowed_tiers=["PUBLIC"]
)
```

---

## Complete Example: Multi-Framework Stack

```python
"""
Complete Lacuna integration with LlamaIndex, LangChain, 
Qdrant, Kagi, and local LLM.
"""
from lacuna import PrivacyAwareRAG
from lacuna.config import load_config

# Vector databases
from qdrant_client import QdrantClient

# LLM
from lacuna.integrations.llm import VLLMBackend

# Embeddings
from sentence_transformers import SentenceTransformer

# Search
from lacuna.integrations.search import KagiSearch

# 1. Initialize components
config = load_config("config/")

# Local vector DB
qdrant = QdrantClient(url="http://localhost:6333")

# Local LLM for classification
llm = VLLMBackend(
    model="meta-llama/Llama-2-70b-chat-hf",
    api_base="http://localhost:8000"
)

# Local embeddings
embeddings = SentenceTransformer("BAAI/bge-large-en-v1.5")

# Web search (for PUBLIC queries only)
kagi = KagiSearch(api_key=config.kagi_api_key)

# 2. Initialize Lacuna
rag = PrivacyAwareRAG(
    config=config,
    local_vectordb=qdrant,
    llm_backend=llm,
    embeddings=embeddings,
    web_search=kagi,
    strategy="conservative"
)

# 3. Use with any framework

# LlamaIndex
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore

vector_store = QdrantVectorStore(client=qdrant, collection_name="docs")
index = VectorStoreIndex.from_vector_store(vector_store)

# Wrap index with Lacuna
from lacuna.integrations.llamaindex import wrap_index
privacy_aware_index = wrap_index(index, rag.classifier)

# LangChain
from langchain_community.vectorstores import Qdrant as LangChainQdrant

lc_vectorstore = LangChainQdrant(
    client=qdrant,
    collection_name="docs",
    embeddings=embeddings
)

# Wrap retriever with Lacuna
from lacuna.integrations.langchain import wrap_retriever
privacy_aware_retriever = wrap_retriever(
    lc_vectorstore.as_retriever(),
    rag.classifier
)

# 4. Query - works with both frameworks
response = rag.query("How do we handle authentication?")
# → Automatic classification and routing
```

---

## Middleware Pattern

For custom frameworks or direct integration:

```python
from lacuna.middleware import ClassificationMiddleware

# Your custom RAG pipeline
class CustomRAGPipeline:
    def __init__(self, local_db, web_search):
        self.local_db = local_db
        self.web_search = web_search
    
    def query(self, text: str) -> str:
        # Your custom logic
        pass

# Wrap with Lacuna middleware
pipeline = CustomRAGPipeline(local_db, web_search)
privacy_aware_pipeline = ClassificationMiddleware(
    pipeline=pipeline,
    classifier_config="config/",
    routing_strategy="balanced"
)

# Middleware intercepts queries for classification
response = privacy_aware_pipeline.query("Your query")
```

---

## Configuration Examples

### Multi-Source Configuration

```yaml
# config/sources.yaml
sources:
  local:
    - name: "proprietary_qdrant"
      type: "qdrant"
      url: "http://localhost:6333"
      collection: "proprietary"
      tier: "PROPRIETARY"
    
    - name: "internal_chromadb"
      type: "chromadb"
      path: "./chroma_internal"
      collection: "internal"
      tier: "INTERNAL"
  
  web:
    - name: "kagi"
      type: "kagi"
      api_key: "${KAGI_API_KEY}"
      tier: "PUBLIC"
      rate_limit: 300  # requests/hour
    
    - name: "searxng"
      type: "searxng"
      url: "https://searxng.local"
      tier: "PUBLIC"
      fallback: true  # Use if Kagi fails

routing:
  PROPRIETARY:
    sources: ["proprietary_qdrant"]
    web_search: false
  
  INTERNAL:
    sources: ["proprietary_qdrant", "internal_chromadb"]
    web_search: false
  
  PUBLIC:
    sources: ["proprietary_qdrant", "internal_chromadb"]
    web_search: true
    web_sources: ["kagi", "searxng"]
```

### Framework-Specific Config

```yaml
# config/integrations.yaml
integrations:
  llamaindex:
    enabled: true
    response_mode: "tree_summarize"
    similarity_top_k: 5
    streaming: true
  
  langchain:
    enabled: true
    chain_type: "stuff"
    return_source_documents: true
    max_tokens_limit: 3000
  
  embeddings:
    provider: "sentence_transformers"
    model: "BAAI/bge-large-en-v1.5"
    device: "cuda"
    normalize: true
  
  llm:
    provider: "vllm"
    endpoint: "http://localhost:8000"
    model: "meta-llama/Llama-2-70b-chat-hf"
    temperature: 0.1
    max_tokens: 500
```

---

## Best Practices

### 1. Always Initialize Lacuna First

```python
# ✅ Good: Lacuna wraps framework components
config = load_config("config/")
rag = PrivacyAwareRAG(config=config)
index = wrap_index(llamaindex_index, rag.classifier)

# ❌ Bad: Framework initialized without privacy layer
index = VectorStoreIndex.from_documents(docs)
# No privacy classification!
```

### 2. Use Appropriate Privacy Tiers

```python
# ✅ Good: Separate collections by sensitivity
proprietary_index = create_index(proprietary_docs)
public_index = create_index(public_docs)

# ❌ Bad: Mixing tiers in same index
mixed_index = create_index(proprietary_docs + public_docs)
```

### 3. Test Integration Thoroughly

```python
# Test privacy routing
def test_proprietary_stays_local():
    """Ensure PROPRIETARY queries don't hit web search."""
    response = rag.query("Our customer retention strategy")
    
    assert response.classification.tier == "PROPRIETARY"
    assert not response.used_web_search
    assert len(response.local_sources) > 0

def test_public_uses_web():
    """Ensure PUBLIC queries leverage web search."""
    response = rag.query("Latest Python version")
    
    assert response.classification.tier == "PUBLIC"
    assert response.used_web_search or len(response.local_sources) > 0
```

### 4. Monitor Integration Performance

```python
from lacuna.monitoring import IntegrationMetrics

metrics = IntegrationMetrics()

# Track framework usage
metrics.track_query(
    framework="llamaindex",
    tier="PROPRIETARY",
    latency_ms=150.5,
    sources_used=["qdrant"]
)

# Export to Prometheus
metrics.export_prometheus()
```

---

## Troubleshooting

### Issue: Classification Too Slow

**Symptom**: Integration adds >500ms latency

**Solution**:
```python
# Enable async classification
rag = PrivacyAwareRAG(
    config=config,
    async_classification=True,
    cache_enabled=True,
    cache_size=10000
)
```

### Issue: Wrong Sources Selected

**Symptom**: PUBLIC queries hitting proprietary DB

**Solution**:
```python
# Verify routing configuration
from lacuna.debug import verify_routing

verify_routing(
    query="Test query",
    expected_tier="PUBLIC",
    expected_sources=["web_search"]
)
```

### Issue: Framework Conflict

**Symptom**: LlamaIndex and LangChain interfering

**Solution**:
```python
# Use separate environments or explicit isolation
llamaindex_rag = PrivacyAwareRAG(
    config=config,
    framework="llamaindex"
)

langchain_rag = PrivacyAwareRAG(
    config=config,
    framework="langchain"
)
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [PLUGINS.md](PLUGINS.md) - Plugin development
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- [examples/](../examples/) - Integration code examples

---

*Lacuna integrates seamlessly with your existing RAG stack, adding privacy-awareness without disruption.*
