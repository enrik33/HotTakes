"""
Application configuration and settings.
Loads from environment variables.
"""

from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Environment
    environment: str = "development"  # development, production, test
    debug: bool = False
    log_level: str = "info"

    # Database
    database_url: str = Field(
        "postgresql://debateuser:debatepass@localhost:5432/social_debate"
    )
    database_echo: bool = False

    # Reddit API
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    reddit_username: str = ""
    reddit_password: str = ""

    # API Settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    api_title: str = "HotTakes"

    # Scheduler
    scheduler_enabled: bool = True
    fetch_interval_minutes: int = 30
    classify_interval_hours: int = 6
    cluster_interval_hours: int = 12
    stats_job_interval_hours: int = 1

    # Data Limits
    max_comments_per_topic: int = 25000
    max_comments_per_post: int = 1000
    max_comments_per_fetch: int = 2000
    history_days: int = 30

    # ML/NLP Models
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    toxicity_model: str = "toxigen/roberta-large-toxic-comments"
    sentiment_model: str = "distilbert-base-uncased-finetuned-sst-2-english"

    # Clustering
    n_clusters_per_stance: int = 10  # Target clusters per stance
    min_cluster_size: int = 8
    min_quote_length: int = 40

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "production", "test"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            allowed_str = ", ".join(sorted(allowed))
            raise ValueError(
                f"ENVIRONMENT must be one of: {allowed_str}. Got: '{value}'."
            )
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"debug", "info", "warning", "error", "critical"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            allowed_str = ", ".join(sorted(allowed))
            raise ValueError(
                f"LOG_LEVEL must be one of: {allowed_str}. Got: '{value}'."
            )
        return normalized

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value or "://" not in value:
            raise ValueError(
                "DATABASE_URL must be present and include a valid scheme (e.g., "
                "'postgresql://...' or 'sqlite:///...')."
            )
        scheme = value.split("://", 1)[0].lower()
        if scheme not in {"postgresql", "postgres", "sqlite"}:
            raise ValueError(
                "DATABASE_URL scheme must be one of: postgresql, postgres, sqlite."
            )
        return value

    @field_validator("reddit_client_id", "reddit_client_secret", "reddit_user_agent")
    @classmethod
    def validate_required_reddit_fields(cls, value: str, info) -> str:
        if value is None or not value.strip():
            env_name = info.field_name.upper()
            raise ValueError(f"{env_name} is required and cannot be empty.")
        return value.strip()

    @field_validator("fetch_interval_minutes")
    @classmethod
    def validate_fetch_interval(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("FETCH_INTERVAL_MINUTES must be greater than 0.")
        return value

    @field_validator("min_cluster_size")
    @classmethod
    def validate_min_cluster_size(cls, value: int) -> int:
        if value < 2:
            raise ValueError("MIN_CLUSTER_SIZE must be greater than or equal to 2.")
        return value

    @model_validator(mode="after")
    def validate_data_limits(self):
        if self.max_comments_per_topic < self.max_comments_per_fetch:
            raise ValueError(
                "MAX_COMMENTS_PER_TOPIC must be greater than or equal to "
                "MAX_COMMENTS_PER_FETCH."
            )
        return self


# Global settings instance
settings = Settings()
