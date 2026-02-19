"""
Application configuration and settings.
Loads from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = "development"  # development, production
    debug: bool = False
    log_level: str = "info"

    # Database
    database_url: str = "sqlite:///./test.db"  # Override with PostgreSQL in .env
    database_echo: bool = False

    # Reddit API
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    reddit_username: str = ""
    reddit_password: str = ""

    # API Settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    api_title: str = "Social Debate Analyzer"

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

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
