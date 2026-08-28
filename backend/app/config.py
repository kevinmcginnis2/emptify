from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    port: int = 8000
    mongodb_uri: str = ""
    frontend_url: str = "http://localhost:3000"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/accounts/oauth/callback"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"


settings = Settings()
