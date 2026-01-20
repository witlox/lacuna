# Production Deployment Guide

**Lacuna** - The protected space where your knowledge stays yours

Deploy Lacuna in production with Docker, Kubernetes, and Helm for enterprise-scale privacy-aware RAG.

> **For local development**, see [DEVELOPMENT.md](DEVELOPMENT.md) for the lightweight dev mode that requires no external dependencies.

---

## Production-Ready Configurations

The [`deploy/`](../deploy/) directory contains production-ready configurations:

```
deploy/
├── README.md                      # Deployment overview
├── docker/
│   ├── docker-compose.prod.yaml   # Production multi-replica setup
│   ├── docker-compose.ha.yaml     # High-availability (PostgreSQL replication, Redis Sentinel)
│   ├── nginx.conf                 # Load balancer with rate limiting
│   ├── .env.example               # Environment template
│   └── init-db.sql                # Database initialization
│
└── helm/lacuna/
    ├── Chart.yaml                 # Helm chart definition
    ├── values.yaml                # Default values
    ├── values-production.yaml     # Production values
    └── templates/                 # Kubernetes manifests
```

### Quick Start (Production Docker)

```bash
# Copy and configure environment
cp deploy/docker/.env.example deploy/docker/.env
# Edit deploy/docker/.env with production values

# Start production stack (2 API replicas, Nginx load balancer)
docker compose -f deploy/docker/docker-compose.prod.yaml up -d

# Run database migrations
docker compose -f deploy/docker/docker-compose.prod.yaml --profile migrate up migrate

# Scale API replicas
docker compose -f deploy/docker/docker-compose.prod.yaml up -d --scale lacuna-api=5
```

### Quick Start (High Availability)

```bash
# HA setup includes:
# - 3 API replicas
# - PostgreSQL primary + 2 replicas with PgPool
# - Redis master + 2 replicas with Sentinel
docker compose -f deploy/docker/docker-compose.ha.yaml up -d
```

### Quick Start (Kubernetes/Helm)

```bash
# Add Bitnami repo for PostgreSQL/Redis dependencies
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency update ./deploy/helm/lacuna

# Install with production values
helm install lacuna ./deploy/helm/lacuna \
  -f deploy/helm/lacuna/values-production.yaml \
  --set secrets.databasePassword=YOUR_PASSWORD \
  --set secrets.redisPassword=YOUR_PASSWORD \
  --set ingress.hosts[0].host=lacuna.yourdomain.com
```

---

## Deployment Options

| Method | Best For | Complexity | Scale |
|--------|----------|------------|-------|
| **pip install** | Development, single machine | Low | 1 node |
| **Docker** | Testing, simple production | Low | 1-3 containers |
| **Docker Compose** | Multi-service development | Medium | 1 node |
| **Kubernetes** | Production, enterprise | High | Multi-node |
| **Helm Chart** | Production, GitOps | Medium | Multi-node |

---

## Quick Start

### pip Installation

```bash
# Install Lacuna
pip install lacuna

# With optional dependencies
pip install lacuna[all]  # Everything
pip install lacuna[plugins-enterprise]  # Enterprise plugins
pip install lacuna[llamaindex,langchain]  # Framework integrations

# Verify installation
lacuna --version
lacuna config validate
```

### Docker

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/witlox/lacuna:latest

# Run with config volume
docker run -d \
  --name lacuna \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -e LACUNA_CONFIG_PATH=/app/config \
  ghcr.io/witlox/lacuna:latest

# Check health
curl http://localhost:8000/health
```

### Docker Compose

```bash
# Clone repository
git clone https://github.com/witlox/lacuna.git
cd lacuna

# Start stack
docker-compose up -d

# Verify services
docker-compose ps
```

---

## Docker Deployment

### Official Images

```bash
# Available tags
ghcr.io/witlox/lacuna:latest           # Latest stable
ghcr.io/witlox/lacuna:0.1.0            # Specific version
ghcr.io/witlox/lacuna:0.1.0-slim       # Minimal (no GPU)
ghcr.io/witlox/lacuna:0.1.0-gpu        # With CUDA support
```

### Dockerfile

```dockerfile
# Base image with Python 3.11
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY lacuna/ ./lacuna/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 lacuna && \
    chown -R lacuna:lacuna /app

USER lacuna

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run classifier service
CMD ["python", "-m", "lacuna.server", "--host", "0.0.0.0", "--port", "8000"]
```

### GPU-Enabled Dockerfile

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 as base

# Install Python
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch with CUDA support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy and install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY lacuna/ ./lacuna/
COPY config/ ./config/

# Expose port
EXPOSE 8000

# Run with GPU
CMD ["python3", "-m", "lacuna.server", "--host", "0.0.0.0", "--port", "8000", "--device", "cuda"]
```

### Environment Variables

```bash
# Core configuration
LACUNA_CONFIG_PATH=/app/config
LACUNA_LOG_LEVEL=INFO
LACUNA_LOG_FORMAT=json

# Database
LACUNA_POSTGRES_URL=postgresql://user:pass@postgres:5432/lacuna
LACUNA_POSTGRES_POOL_SIZE=20

# LLM backend
LACUNA_LLM_BACKEND=vllm
LACUNA_LLM_ENDPOINT=http://vllm:8000
LACUNA_LLM_MODEL=meta-llama/Llama-3.1-70B-Instruct

# Embeddings
LACUNA_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
LACUNA_EMBEDDING_DEVICE=cuda

# Cache
LACUNA_REDIS_URL=redis://redis:6379
LACUNA_CACHE_TTL=3600

# Metrics
LACUNA_PROMETHEUS_PORT=9090
LACUNA_LOKI_URL=http://loki:3100

# Security
LACUNA_API_KEY=${LACUNA_API_KEY}
LACUNA_VAULT_URL=http://vault:8200
LACUNA_VAULT_TOKEN=${VAULT_TOKEN}
```

### Docker Compose Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Lacuna classifier service
  lacuna:
    image: ghcr.io/witlox/lacuna:latest
    container_name: lacuna
    ports:
      - "8000:8000"  # API
      - "9090:9090"  # Prometheus metrics
    volumes:
      - ./config:/app/config:ro
      - ./data:/app/data
    environment:
      - LACUNA_CONFIG_PATH=/app/config
      - LACUNA_LOG_LEVEL=INFO
      - LACUNA_POSTGRES_URL=postgresql://lacuna:${POSTGRES_PASSWORD}@postgres:5432/lacuna
      - LACUNA_REDIS_URL=redis://redis:6379
      - LACUNA_LLM_ENDPOINT=http://vllm:8000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - lacuna-net

  # PostgreSQL for lineage/audit
  postgres:
    image: postgres:16-alpine
    container_name: lacuna-postgres
    environment:
      - POSTGRES_DB=lacuna
      - POSTGRES_USER=lacuna
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lacuna"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - lacuna-net

  # Redis for caching
  redis:
    image: redis:7-alpine
    container_name: lacuna-redis
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - lacuna-net

  # Qdrant vector database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: lacuna-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    restart: unless-stopped
    networks:
      - lacuna-net

  # vLLM for LLM backend (requires GPU)
  vllm:
    image: vllm/vllm-openai:latest
    container_name: lacuna-vllm
    ports:
      - "8001:8000"
    environment:
      - CUDA_VISIBLE_DEVICES=0,1,2,3  # 4 GPUs
    command: >
      --model meta-llama/Llama-3.1-70B-Instruct
      --tensor-parallel-size 4
      --max-model-len 32768
      --gpu-memory-utilization 0.95
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 4
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - lacuna-net

  # OPA for policy-as-code
  opa:
    image: openpolicyagent/opa:latest
    container_name: lacuna-opa
    ports:
      - "8181:8181"
    command: run --server --addr :8181 /policies
    volumes:
      - ./policies:/policies:ro
    restart: unless-stopped
    networks:
      - lacuna-net

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: lacuna-prometheus
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped
    networks:
      - lacuna-net

  # Loki for logs
  loki:
    image: grafana/loki:latest
    container_name: lacuna-loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped
    networks:
      - lacuna-net

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: lacuna-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    restart: unless-stopped
    networks:
      - lacuna-net

  # Vault for secrets
  vault:
    image: hashicorp/vault:latest
    container_name: lacuna-vault
    ports:
      - "8200:8200"
    environment:
      - VAULT_DEV_ROOT_TOKEN_ID=${VAULT_TOKEN}
      - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
    cap_add:
      - IPC_LOCK
    restart: unless-stopped
    networks:
      - lacuna-net

volumes:
  postgres-data:
  redis-data:
  qdrant-data:
  prometheus-data:
  loki-data:
  grafana-data:

networks:
  lacuna-net:
    driver: bridge
```

### Starting the Stack

```bash
# Create .env file
cat > .env <<EOF
POSTGRES_PASSWORD=your_secure_password
GRAFANA_PASSWORD=your_grafana_password
VAULT_TOKEN=your_vault_token
LACUNA_API_KEY=your_api_key
EOF

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f lacuna

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Kubernetes 1.25+
kubectl version

# Helm 3.10+
helm version

# Storage class for persistent volumes
kubectl get storageclass
```

### Namespace Setup

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lacuna
  labels:
    name: lacuna
    monitoring: enabled
```

```bash
kubectl apply -f namespace.yaml
```

### ConfigMaps

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lacuna-config
  namespace: lacuna
data:
  config.yaml: |
    classification:
      strategy: conservative
      layers:
        heuristic:
          enabled: true
          priority: 1
        embedding:
          enabled: true
          priority: 2
          model: BAAI/bge-large-en-v1.5
        llm:
          enabled: true
          priority: 3
          endpoint: http://vllm:8000
    
    routing:
      PROPRIETARY:
        local_rag: true
        web_search: false
      INTERNAL:
        local_rag: true
        web_search: false
      PUBLIC:
        local_rag: true
        web_search: true
    
    lineage:
      enabled: true
      postgres_url: postgresql://lacuna:password@postgres:5432/lacuna
      sampling_rate: 1.0
    
    cache:
      enabled: true
      redis_url: redis://redis:6379
      ttl: 3600
    
    metrics:
      enabled: true
      prometheus_port: 9090
    
    logging:
      level: INFO
      format: json
      loki_url: http://loki:3100

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: lacuna-proprietary-terms
  namespace: lacuna
data:
  proprietary_terms.yaml: |
    projects:
      - project_apollo
      - project_artemis
      - skunkworks
    
    customers:
      - customer_alpha
      - customer_beta
      - vip_client
    
    internal_terms:
      - confidential
      - internal only
      - do not distribute
```

### Secrets

```bash
# Create secrets from files
kubectl create secret generic lacuna-secrets \
  --from-literal=postgres-password=your_secure_password \
  --from-literal=api-key=your_api_key \
  --from-literal=kagi-api-key=your_kagi_key \
  --namespace=lacuna

# Or from YAML
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: lacuna-secrets
  namespace: lacuna
type: Opaque
stringData:
  postgres-password: your_secure_password
  api-key: your_api_key
  kagi-api-key: your_kagi_key
EOF
```

### Deployments

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lacuna-classifier
  namespace: lacuna
  labels:
    app: lacuna
    component: classifier
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lacuna
      component: classifier
  template:
    metadata:
      labels:
        app: lacuna
        component: classifier
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      
      containers:
      - name: lacuna
        image: ghcr.io/witlox/lacuna:0.1.0
        imagePullPolicy: IfNotPresent
        
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        - name: metrics
          containerPort: 9090
          protocol: TCP
        
        env:
        - name: LACUNA_CONFIG_PATH
          value: /app/config
        - name: LACUNA_LOG_LEVEL
          value: INFO
        - name: LACUNA_POSTGRES_URL
          value: postgresql://lacuna:$(POSTGRES_PASSWORD)@postgres:5432/lacuna
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: lacuna-secrets
              key: postgres-password
        - name: LACUNA_REDIS_URL
          value: redis://redis:6379
        - name: LACUNA_API_KEY
          valueFrom:
            secretKeyRef:
              name: lacuna-secrets
              key: api-key
        
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: proprietary-terms
          mountPath: /app/config/proprietary_terms.yaml
          subPath: proprietary_terms.yaml
          readOnly: true
        
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
        
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      
      volumes:
      - name: config
        configMap:
          name: lacuna-config
      - name: proprietary-terms
        configMap:
          name: lacuna-proprietary-terms

---
# vLLM deployment (requires GPU nodes)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm
  namespace: lacuna
  labels:
    app: lacuna
    component: llm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lacuna
      component: llm
  template:
    metadata:
      labels:
        app: lacuna
        component: llm
    spec:
      nodeSelector:
        nvidia.com/gpu: "true"  # Schedule on GPU nodes
      
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3"
        
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model
        - meta-llama/Llama-3.1-70B-Instruct
        - --tensor-parallel-size
        - "4"
        - --max-model-len
        - "32768"
        - --gpu-memory-utilization
        - "0.95"
        
        resources:
          requests:
            nvidia.com/gpu: 4
            memory: "200Gi"
            cpu: "16"
          limits:
            nvidia.com/gpu: 4
            memory: "256Gi"
            cpu: "32"
        
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 120
          periodSeconds: 30
          timeoutSeconds: 10
```

### Services

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: lacuna
  namespace: lacuna
  labels:
    app: lacuna
    component: classifier
spec:
  type: ClusterIP
  selector:
    app: lacuna
    component: classifier
  ports:
  - name: http
    port: 8000
    targetPort: http
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: metrics
    protocol: TCP

---
apiVersion: v1
kind: Service
metadata:
  name: vllm
  namespace: lacuna
  labels:
    app: lacuna
    component: llm
spec:
  type: ClusterIP
  selector:
    app: lacuna
    component: llm
  ports:
  - name: http
    port: 8000
    targetPort: http
    protocol: TCP

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: lacuna
spec:
  type: ClusterIP
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: lacuna
spec:
  type: ClusterIP
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lacuna
  namespace: lacuna
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: lacuna-basic-auth
spec:
  tls:
  - hosts:
    - lacuna.example.com
    secretName: lacuna-tls
  rules:
  - host: lacuna.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lacuna
            port:
              number: 8000
```

### Apply Kubernetes Manifests

```bash
# Apply all manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment
kubectl get pods -n lacuna
kubectl logs -f deployment/lacuna-classifier -n lacuna

# Check services
kubectl get svc -n lacuna

# Test service
kubectl port-forward svc/lacuna 8000:8000 -n lacuna
curl http://localhost:8000/health
```

---

## Helm Deployment

### Install Helm Chart

```bash
# Add Lacuna Helm repository
helm repo add lacuna https://witlox.github.io/lacuna-helm
helm repo update

# Install with default values
helm install lacuna lacuna/lacuna --namespace lacuna --create-namespace

# Install with custom values
helm install lacuna lacuna/lacuna \
  --namespace lacuna \
  --create-namespace \
  --values values.yaml

# Upgrade
helm upgrade lacuna lacuna/lacuna \
  --namespace lacuna \
  --values values.yaml

# Uninstall
helm uninstall lacuna --namespace lacuna
```

### Custom Values

```yaml
# values.yaml

# Image configuration
image:
  repository: ghcr.io/witlox/lacuna
  tag: "0.1.0"
  pullPolicy: IfNotPresent

# Replicas
replicaCount: 3

# Resources
resources:
  requests:
    memory: "4Gi"
    cpu: "2"
  limits:
    memory: "8Gi"
    cpu: "4"

# Autoscaling
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Configuration
config:
  classification:
    strategy: conservative
  
  routing:
    proprietary:
      local_rag: true
      web_search: false
    public:
      local_rag: true
      web_search: true

# Proprietary terms
proprietaryTerms:
  projects:
    - project_apollo
    - project_artemis
  customers:
    - customer_alpha

# PostgreSQL (for lineage)
postgresql:
  enabled: true
  auth:
    username: lacuna
    password: changeme
    database: lacuna
  primary:
    persistence:
      enabled: true
      size: 20Gi
  resources:
    requests:
      memory: "2Gi"
      cpu: "1"
    limits:
      memory: "4Gi"
      cpu: "2"

# Redis (for caching)
redis:
  enabled: true
  auth:
    enabled: false
  master:
    persistence:
      enabled: true
      size: 8Gi
  resources:
    requests:
      memory: "2Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "1"

# Qdrant (vector database)
qdrant:
  enabled: true
  persistence:
    enabled: true
    size: 50Gi
  resources:
    requests:
      memory: "8Gi"
      cpu: "2"
    limits:
      memory: "16Gi"
      cpu: "4"

# vLLM (LLM backend)
vllm:
  enabled: true
  model: "meta-llama/Llama-3.1-70B-Instruct"
  tensorParallelSize: 4
  maxModelLen: 32768
  gpuMemoryUtilization: 0.95
  
  nodeSelector:
    nvidia.com/gpu: "true"
  
  resources:
    requests:
      nvidia.com/gpu: 4
      memory: "200Gi"
      cpu: "16"
    limits:
      nvidia.com/gpu: 4
      memory: "256Gi"
      cpu: "32"

# OPA (policy-as-code)
opa:
  enabled: true
  policies:
    base: |
      package lacuna.classification
      # Policy content here

# Monitoring
monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
    adminPassword: changeme
  loki:
    enabled: true

# Ingress
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: lacuna.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: lacuna-tls
      hosts:
        - lacuna.example.com

# Security
security:
  apiKey:
    enabled: true
    existingSecret: lacuna-secrets
    key: api-key
  
  vault:
    enabled: true
    address: http://vault:8200
    token: changeme

# Service
service:
  type: ClusterIP
  port: 8000
  metricsPort: 9090
```

### Deploy with Helm

```bash
# Create values file
cat > my-values.yaml <<EOF
replicaCount: 5

postgresql:
  auth:
    password: $(openssl rand -base64 32)

grafana:
  adminPassword: $(openssl rand -base64 16)

ingress:
  hosts:
    - host: lacuna.mycompany.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: lacuna-tls
      hosts:
        - lacuna.mycompany.com
EOF

# Install
helm install lacuna lacuna/lacuna \
  --namespace lacuna \
  --create-namespace \
  --values my-values.yaml

# Check status
helm status lacuna -n lacuna
kubectl get pods -n lacuna
```

---

## Production Checklist

### Security

- [ ] Change all default passwords
- [ ] Enable TLS/SSL for all services
- [ ] Configure network policies
- [ ] Enable pod security policies
- [ ] Set up RBAC
- [ ] Use secrets management (Vault)
- [ ] Enable API authentication
- [ ] Configure rate limiting
- [ ] Set up audit logging

### High Availability

- [ ] Deploy multiple replicas (≥3)
- [ ] Configure pod anti-affinity
- [ ] Set up horizontal pod autoscaling
- [ ] Configure liveness/readiness probes
- [ ] Set resource requests/limits
- [ ] Enable persistent storage
- [ ] Configure backup/restore

### Monitoring

- [ ] Deploy Prometheus
- [ ] Deploy Grafana with dashboards
- [ ] Configure alerting rules
- [ ] Set up Loki for logs
- [ ] Enable distributed tracing
- [ ] Configure health checks
- [ ] Set up uptime monitoring

### Performance

- [ ] Enable Redis caching
- [ ] Configure connection pooling
- [ ] Optimize resource allocation
- [ ] Set up CDN (if applicable)
- [ ] Enable compression
- [ ] Configure query timeouts
- [ ] Tune PostgreSQL

### Compliance

- [ ] Enable audit logging
- [ ] Configure data retention
- [ ] Set up lineage tracking
- [ ] Document privacy policies
- [ ] Enable encryption at rest
- [ ] Configure access controls
- [ ] Set up compliance dashboards

---

## Monitoring & Observability

### Prometheus Metrics

```yaml
# prometheus-rules.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: lacuna
data:
  lacuna.rules: |
    groups:
    - name: lacuna
      interval: 30s
      rules:
      
      # High error rate
      - alert: HighErrorRate
        expr: rate(lacuna_classification_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High classification error rate"
          description: "Error rate is {{ $value }} errors/sec"
      
      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, lacuna_classification_latency_seconds_bucket) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High classification latency"
          description: "P95 latency is {{ $value }} seconds"
      
      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: rate(lacuna_cache_hits_total[5m]) / (rate(lacuna_cache_hits_total[5m]) + rate(lacuna_cache_misses_total[5m])) < 0.7
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value }}%"
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Lacuna Production",
    "panels": [
      {
        "title": "Requests/sec",
        "targets": [{
          "expr": "rate(lacuna_requests_total[5m])"
        }]
      },
      {
        "title": "P95 Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, lacuna_classification_latency_seconds_bucket)"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(lacuna_classification_errors_total[5m])"
        }]
      },
      {
        "title": "Tier Distribution",
        "targets": [{
          "expr": "sum by (tier) (rate(lacuna_classification_tier_total[5m]))"
        }]
      }
    ]
  }
}
```

---

## Troubleshooting

### Pod Crashes

```bash
# Check pod status
kubectl get pods -n lacuna

# View logs
kubectl logs -f deployment/lacuna-classifier -n lacuna

# Describe pod
kubectl describe pod lacuna-classifier-xxx -n lacuna

# Check events
kubectl get events -n lacuna --sort-by='.lastTimestamp'
```

### Database Issues

```bash
# Check PostgreSQL connectivity
kubectl exec -it deployment/lacuna-classifier -n lacuna -- \
  psql postgresql://lacuna:password@postgres:5432/lacuna -c "SELECT 1;"

# Check database size
kubectl exec -it postgres-0 -n lacuna -- \
  psql -U lacuna -c "SELECT pg_size_pretty(pg_database_size('lacuna'));"
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n lacuna

# Check HPA status
kubectl get hpa -n lacuna

# View metrics
kubectl port-forward svc/lacuna 9090:9090 -n lacuna
curl http://localhost:9090/metrics
```

---

---

## Authentication

Lacuna supports two authentication methods, designed for enterprise deployment behind a reverse proxy or API gateway.

### Authentication Methods

| Method | Use Case | Header/Mechanism |
|--------|----------|------------------|
| **Reverse Proxy Headers** | Human users via OIDC/SSO | X-User, X-Email, X-Groups |
| **API Keys** | Service accounts, automation | Authorization: Bearer lac_xxx |

### Reverse Proxy Authentication (OIDC/SSO)

In production, Lacuna runs behind a reverse proxy (oauth2-proxy, Traefik, nginx-oidc, etc.) that handles authentication and forwards user identity via headers:

```yaml
# Environment variables (config)
LACUNA_AUTH_USER_HEADER=X-User         # User ID header
LACUNA_AUTH_EMAIL_HEADER=X-Email       # Email header
LACUNA_AUTH_GROUPS_HEADER=X-Groups     # Comma-separated groups
LACUNA_AUTH_NAME_HEADER=X-Name         # Display name header
LACUNA_AUTH_ADMIN_GROUP=lacuna-admins  # Group for admin access
```

Example nginx configuration with oauth2-proxy:

```nginx
location / {
    auth_request /oauth2/auth;
    auth_request_set $user   $upstream_http_x_auth_request_user;
    auth_request_set $email  $upstream_http_x_auth_request_email;
    auth_request_set $groups $upstream_http_x_auth_request_groups;
    
    proxy_set_header X-User $user;
    proxy_set_header X-Email $email;
    proxy_set_header X-Groups $groups;
    
    proxy_pass http://lacuna:8000;
}
```

### API Key Authentication (Service Accounts)

For service accounts (dbt, CI/CD pipelines, Databricks), use API keys:

1. **Create via Admin UI**: Navigate to Admin > API Keys
2. **Create via CLI**:
   ```bash
   lacuna admin apikey create \
     --name "dbt-production" \
     --service-account "svc-dbt" \
     --groups "data-engineers"
   ```

3. **Use in requests**:
   ```bash
   curl -H "Authorization: Bearer lac_your_key_here" \
        https://lacuna.example.com/api/v1/classify
   ```

API key format: `lac_` prefix followed by 32+ secure random characters.

### Role-Based Access Control

| Role | Access | Determined By |
|------|--------|---------------|
| **Admin** | Full access, API key management, config | Member of `lacuna-admins` group |
| **User** | Query, classify, view own audit logs | Any authenticated user |

### Dev Mode Authentication

In dev mode (`lacuna dev`), authentication is bypassed and a default admin user is used:

```python
# Automatic dev user
user_id: "dev-user"
email: "dev@localhost"
groups: ["lacuna-admins", "developers"]
is_admin: True
```

**Warning**: Never use dev mode in production.

### Security Best Practices

1. **Always use TLS** - API keys are sensitive credentials
2. **Rotate API keys regularly** - Set expiration dates
3. **Use service-specific keys** - One key per service for auditability
4. **Trust only internal proxies** - Verify X-Forwarded-For headers
5. **Monitor API key usage** - Check last_used_at in admin UI

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [LINEAGE.md](LINEAGE.md) - Audit and compliance
- [POLICY_AS_CODE.md](POLICY_AS_CODE.md) - OPA configuration

---

*Deploy Lacuna confidently in production with enterprise-grade reliability and observability.*
