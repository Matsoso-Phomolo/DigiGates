from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:password@localhost:3306/digigates"
    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 1440
    frontend_origin: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

