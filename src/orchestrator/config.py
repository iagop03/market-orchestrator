from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discovery_api_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./market_orchestrator.db"
    github_token: str = ""
    slack_webhook_url: str = ""
    antcrew_path: str = "antcrew"
    antcrew_model: str = "claude"
