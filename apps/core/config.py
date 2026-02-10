from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")
    PROJECT_NAME: str = "Habit API"
    DATABASE_URL: str
    SECRET_KEY: str = "secret_key"
    DEBUG: bool = False
    API_BASE_URL: str = "http://localhost:8000"


settings = Settings()
