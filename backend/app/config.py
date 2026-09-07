from functools import lru_cache
from urllib.parse import quote_plus
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "digigates"
    mysql_user: str = "digigates"
    mysql_password: str = Field(default="", repr=False)
    secret_key: str = Field(default="development-only-change-me", repr=False)
    access_token_minutes: int = 1440
    frontend_origin: str = "http://localhost:5173"
    sql_echo: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def database_url(self):
        return f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"

@lru_cache
def get_settings(): return Settings()
settings = get_settings()
