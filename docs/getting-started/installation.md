# Installation

Multiple installation options for different use cases.

## Prerequisites

- Python 3.9, 3.10, 3.11, or 3.12
- pip (Python package installer)

## Installation Methods

### From Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/witlox/lacuna.git
cd lacuna

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Install with documentation dependencies
pip install -e ".[docs]"
```

### From PyPI

```bash
# Basic installation
pip install lacuna

# With specific features
pip install lacuna[dev]
pip install lacuna[docs]
```

### Using Docker

```bash
# Pull the latest image
docker pull ghcr.io/witlox/lacuna:latest

# Run with default settings
docker run -d -p 8000:8000 ghcr.io/witlox/lacuna:latest
```

## Optional Dependencies

Lacuna has several optional dependency groups for different features:

### Development Tools

```bash
pip install lacuna[dev]
```

Includes: pytest, black, ruff, mypy, pre-commit

### Documentation

```bash
pip install lacuna[docs]
```

Includes: mkdocs, mkdocs-material

### RAG Framework Integrations

```bash
# LlamaIndex
pip install lacuna[llamaindex]

# LangChain
pip install lacuna[langchain]

# Both
pip install lacuna[llamaindex,langchain]
```

### Vector Database Backends

```bash
# ChromaDB
pip install lacuna[chromadb]

# Milvus
pip install lacuna[milvus]
```

### Classification Plugins

```bash
# Individual users (basic PII detection)
pip install lacuna[plugins-individual]

# Enterprise (includes OPA)
pip install lacuna[plugins-enterprise]

# Healthcare (includes medical NER)
pip install lacuna[plugins-healthcare]

# Finance
pip install lacuna[plugins-finance]

# All plugins
pip install lacuna[plugins-all]
```

### Complete Installation

Install everything:

```bash
pip install lacuna[all]
```

## Verification

Verify the installation:

```bash
# Check version
lacuna --version

# Check available commands
lacuna --help
```

## External Dependencies

Depending on your deployment mode, you may need:

### Development Mode

No external dependencies required. Uses:

- SQLite (bundled with Python)
- In-memory cache

### Production Mode

Recommended external services:

- **PostgreSQL** 13+ - Primary database
- **Redis** 6+ - Caching layer
- **Open Policy Agent (OPA)** - Policy engine (optional)

### Installing External Dependencies

#### PostgreSQL

=== "Ubuntu/Debian"

    ```bash
    sudo apt-get update
    sudo apt-get install postgresql postgresql-contrib
    ```

=== "macOS"

    ```bash
    brew install postgresql@15
    brew services start postgresql@15
    ```

=== "Docker"

    ```bash
    docker run -d \
      --name lacuna-postgres \
      -e POSTGRES_PASSWORD=lacuna \
      -e POSTGRES_DB=lacuna \
      -p 5432:5432 \
      postgres:15
    ```

#### Redis

=== "Ubuntu/Debian"

    ```bash
    sudo apt-get install redis-server
    sudo systemctl start redis
    ```

=== "macOS"

    ```bash
    brew install redis
    brew services start redis
    ```

=== "Docker"

    ```bash
    docker run -d \
      --name lacuna-redis \
      -p 6379:6379 \
      redis:7-alpine
    ```

#### Open Policy Agent (Optional)

=== "Docker"

    ```bash
    docker run -d \
      --name lacuna-opa \
      -p 8181:8181 \
      openpolicyagent/opa:latest \
      run --server
    ```

=== "Binary"

    ```bash
    # Download OPA
    curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
    chmod +x opa

    # Run server
    ./opa run --server
    ```

## Configuration

After installation, configure Lacuna:

```bash
# Copy example config
cp config/example.env .env

# Edit configuration
nano .env
```

Key settings:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/lacuna

# Redis
REDIS_URL=redis://localhost:6379/0

# OPA (optional)
OPA_URL=http://localhost:8181

# Classification
OPENAI_API_KEY=your-key-here  # For LLM classification layer
```

See the [Deployment Guide](../DEPLOYMENT.md) for detailed configuration options.

## Next Steps

- **[Quick Start](quick-start.md)** - Get up and running
- **[User Guide](../USER_GUIDE.md)** - Learn the features
- **[Deployment Guide](../DEPLOYMENT.md)** - Production setup
