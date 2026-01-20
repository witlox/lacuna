"""Application settings and configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str = Field(
        default="postgresql://lacuna:lacuna@localhost:5432/lacuna",
        description="PostgreSQL connection URL",
    )
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    echo: bool = Field(default=False, description="Echo SQL queries")


class RedisSettings(BaseSettings):
    """Redis configuration for caching."""

    url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    ttl: int = Field(default=3600, description="Default cache TTL in seconds")
    enabled: bool = Field(default=True, description="Enable Redis caching")


class ClassificationSettings(BaseSettings):
    """Classification pipeline configuration."""

    strategy: str = Field(
        default="conservative",
        description="Classification strategy: conservative, balanced, or aggressive",
    )
    confidence_threshold: float = Field(
        default=0.9, description="Minimum confidence threshold"
    )
    short_circuit: bool = Field(
        default=True, description="Stop at first high-confidence result"
    )

    # Heuristic layer
    heuristic_enabled: bool = True
    heuristic_priority: int = 60

    # Embedding layer
    embedding_enabled: bool = True
    embedding_priority: int = 70
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_device: str = "cpu"

    # LLM layer
    llm_enabled: bool = True
    llm_priority: int = 80
    llm_endpoint: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: float = 0.1
    llm_max_tokens: int = 500


class LineageSettings(BaseSettings):
    """Lineage tracking configuration."""

    enabled: bool = Field(default=True, description="Enable lineage tracking")
    sampling_rate: float = Field(
        default=1.0, description="Sampling rate for lineage (0.0 to 1.0)"
    )
    max_depth: int = Field(default=10, description="Maximum lineage depth to track")


class AuditSettings(BaseSettings):
    """Audit logging configuration."""

    enabled: bool = Field(default=True, description="Enable audit logging")
    retention_days: int = Field(default=2555, description="Retention period (7 years)")
    verify_integrity: bool = Field(
        default=True, description="Verify hash chain integrity"
    )
    alert_enabled: bool = Field(default=True, description="Enable real-time alerting")


class PolicySettings(BaseSettings):
    """Policy engine configuration."""

    enabled: bool = Field(default=False, description="Enable policy engine")
    opa_endpoint: Optional[str] = Field(default=None, description="OPA server endpoint")
    opa_policy_path: str = Field(
        default="lacuna/classification", description="OPA policy path"
    )
    opa_timeout: float = Field(default=1.0, description="OPA request timeout")


class MonitoringSettings(BaseSettings):
    """Monitoring and metrics configuration."""

    enabled: bool = Field(default=True, description="Enable monitoring")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    loki_url: Optional[str] = Field(default=None, description="Loki logs URL")


class RoutingSettings(BaseSettings):
    """Routing configuration for different tiers."""

    proprietary_local_rag: bool = True
    proprietary_web_search: bool = False

    internal_local_rag: bool = True
    internal_web_search: bool = False

    public_local_rag: bool = True
    public_web_search: bool = True


class AuthSettings(BaseSettings):
    """Authentication configuration."""

    # Enable/disable authentication
    enabled: bool = Field(
        default=True, description="Enable authentication (disabled in dev mode)"
    )

    # Reverse proxy header configuration
    user_header: str = Field(
        default="X-User", description="Header containing username from proxy"
    )
    email_header: str = Field(
        default="X-Email", description="Header containing email from proxy"
    )
    groups_header: str = Field(
        default="X-Groups", description="Header containing comma-separated groups"
    )
    name_header: str = Field(
        default="X-Name", description="Header containing display name"
    )

    # Admin configuration
    admin_group: str = Field(
        default="lacuna-admins", description="Group name for admin access"
    )

    # API key configuration
    api_key_header: str = Field(
        default="Authorization", description="Header for API key (Bearer token)"
    )
    api_key_prefix: str = Field(
        default="Bearer", description="Prefix for API key in header"
    )

    # Security settings
    trusted_proxies: list[str] = Field(
        default_factory=lambda: [
            "127.0.0.1",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ],
        description="Trusted proxy IP ranges",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="LACUNA_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    # Application settings
    app_name: str = "Lacuna"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Paths
    config_path: Path = Field(
        default=Path("config"), description="Configuration directory"
    )
    data_path: Path = Field(default=Path("data"), description="Data directory")
    models_path: Path = Field(default=Path("models"), description="Models directory")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    api_port: int = Field(default=8000, description="API port")
    api_key: Optional[str] = Field(
        default=None, description="API key for authentication"
    )

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    classification: ClassificationSettings = Field(
        default_factory=ClassificationSettings
    )
    lineage: LineageSettings = Field(default_factory=LineageSettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    policy: PolicySettings = Field(default_factory=PolicySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    routing: RoutingSettings = Field(default_factory=RoutingSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)

    # Proprietary terms
    proprietary_projects: list[str] = Field(default_factory=list)
    proprietary_customers: list[str] = Field(default_factory=list)
    proprietary_terms: list[str] = Field(default_factory=list)

    @field_validator("config_path", "data_path", "models_path")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure path exists."""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_config(config_path: Optional[Path] = None) -> dict[str, Any]:
    """Load configuration from YAML files."""
    import yaml

    if config_path is None:
        config_path = Path("config")

    config: dict[str, Any] = {}

    # Load main config
    config_file = config_path / "default.yaml"
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

    # Load proprietary terms
    terms_file = config_path / "proprietary_terms.yaml"
    if terms_file.exists():
        with open(terms_file) as f:
            terms = yaml.safe_load(f) or {}
            config["proprietary_projects"] = terms.get("projects", [])
            config["proprietary_customers"] = terms.get("customers", [])
            config["proprietary_terms"] = terms.get("terms", [])

    return config
