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

    @property
    def async_database_url(self) -> str:
        """Ensure the URL uses the asyncpg driver."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis (optional fixed-window rate limiting when not in test)
    redis_url: str = "redis://localhost:6380/0"
    redis_rate_limiting: bool = True

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

    # Composio
    composio_api_key: str = ""

    # OAuth — provider client credentials (set per-provider as needed)
    github_client_id: str = ""
    github_client_secret: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    notion_client_id: str = ""
    notion_client_secret: str = ""
    atlassian_client_id: str = ""
    atlassian_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    linear_client_id: str = ""
    linear_client_secret: str = ""
    gitlab_client_id: str = ""
    gitlab_client_secret: str = ""
    zoom_client_id: str = ""
    zoom_client_secret: str = ""
    dropbox_client_id: str = ""
    dropbox_client_secret: str = ""
    figma_client_id: str = ""
    figma_client_secret: str = ""
    asana_client_id: str = ""
    asana_client_secret: str = ""
    hubspot_client_id: str = ""
    hubspot_client_secret: str = ""

    # Stripe billing (optional)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""  # e.g. price_xxx for subscription mode

    # OIDC SSO (optional — OpenID Connect authorization code flow)
    oidc_issuer_url: str = ""  # e.g. https://login.microsoftonline.com/{tenant}/v2.0
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_path: str = "/api/auth/oidc/callback"  # full URL built from api_url + path

    # S3
    s3_endpoint: str = "http://localhost:9002"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "recall-files"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def use_redis_rate_limiter(self) -> bool:
        """Use Redis for HTTP rate limits in multi-replica deployments."""
        if self.app_env == "test":
            return False
        return self.redis_rate_limiting


settings = Settings()
