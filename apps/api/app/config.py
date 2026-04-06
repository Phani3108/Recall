from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://recall:recall@localhost:5434/recall"

    # Redis
    redis_url: str = "redis://localhost:6380/0"

    # Weaviate
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str = ""

    # LiteLLM
    litellm_proxy_url: str = "http://localhost:4000"
    litellm_master_key: str = "sk-recall-dev"

    # LLM Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Authentik
    authentik_url: str = "http://localhost:9000"
    authentik_token: str = ""
    authentik_client_id: str = "recall"
    authentik_client_secret: str = ""

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "recall"

    # Composio
    composio_api_key: str = ""

    # S3
    s3_endpoint: str = "http://localhost:9002"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "recall-files"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
