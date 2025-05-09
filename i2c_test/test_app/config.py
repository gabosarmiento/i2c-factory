# before: from pydantic import BaseSettings
# now that BaseSettings lives in its own package:
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test_app.db"
    API_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"

settings = Settings()
