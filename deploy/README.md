# Lacuna Production Deployment

This directory contains deployment configurations for running Lacuna at scale.

## Directory Structure

```
deploy/
├── docker/                    # Docker Compose configurations
│   ├── docker-compose.prod.yaml    # Production multi-replica setup
│   ├── docker-compose.ha.yaml      # High-availability setup
│   └── .env.example                # Environment variables template
│
└── helm/                      # Kubernetes Helm charts
    └── lacuna/
        ├── Chart.yaml
        ├── values.yaml
        ├── values-production.yaml
        └── templates/
```

## Docker Compose Production

### Quick Start

```bash
# Copy environment template
cp deploy/docker/.env.example deploy/docker/.env

# Edit with your production values
vim deploy/docker/.env

# Start production stack
docker compose -f deploy/docker/docker-compose.prod.yaml up -d

# Run migrations
docker compose -f deploy/docker/docker-compose.prod.yaml --profile migrate up migrate

# Scale API replicas
docker compose -f deploy/docker/docker-compose.prod.yaml up -d --scale lacuna-api=3
```

### High Availability

For HA deployments with replicated PostgreSQL and Redis clustering:

```bash
docker compose -f deploy/docker/docker-compose.ha.yaml up -d
```

## Kubernetes Helm

### Prerequisites

- Kubernetes cluster (1.24+)
- Helm 3.x
- kubectl configured

### Installation

```bash
# Add required repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install with default values (development)
helm install lacuna ./deploy/helm/lacuna

# Install for production
helm install lacuna ./deploy/helm/lacuna \
  -f deploy/helm/lacuna/values-production.yaml \
  --set secrets.databasePassword=<your-password> \
  --set secrets.redisPassword=<your-password>

# Upgrade existing installation
helm upgrade lacuna ./deploy/helm/lacuna \
  -f deploy/helm/lacuna/values-production.yaml
```

### Configuration

Key configuration in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of API replicas | `2` |
| `image.tag` | Container image tag | `latest` |
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `1Gi` |
| `postgresql.enabled` | Deploy PostgreSQL | `true` |
| `redis.enabled` | Deploy Redis | `true` |
| `opa.enabled` | Deploy OPA | `true` |
| `ingress.enabled` | Enable Ingress | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |

### Production Recommendations

1. **Use external databases**: Set `postgresql.enabled=false` and configure `externalDatabase`
2. **Enable autoscaling**: Set `autoscaling.enabled=true`
3. **Configure resource limits**: Adjust based on load testing
4. **Enable network policies**: Set `networkPolicy.enabled=true`
5. **Use TLS**: Configure `ingress.tls`

## Monitoring

Both deployments expose Prometheus metrics at `/metrics`. Configure your monitoring stack:

```yaml
# Prometheus scrape config
- job_name: lacuna
  static_configs:
    - targets: ['lacuna-api:8000']
  metrics_path: /metrics
```

## Backup and Recovery

### PostgreSQL Backup

```bash
# Docker Compose
docker exec lacuna-postgres pg_dump -U lacuna lacuna > backup.sql

# Kubernetes
kubectl exec -it lacuna-postgresql-0 -- pg_dump -U lacuna lacuna > backup.sql
```

### Restore

```bash
# Docker Compose
cat backup.sql | docker exec -i lacuna-postgres psql -U lacuna lacuna

# Kubernetes
cat backup.sql | kubectl exec -i lacuna-postgresql-0 -- psql -U lacuna lacuna
```
