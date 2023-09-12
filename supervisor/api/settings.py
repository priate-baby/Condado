from enum import Enum
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Environment(str, Enum):
    LOCAL = 'local'
    DEV = 'dev'
    PROD = 'prod'

class DbPlatform(str, Enum):
    MONGO = 'mongo'
    POSTGRES = 'postgres'

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='/.condado/settings.env',
        env_prefix='condado_',
        env_file_encoding='utf-8'
    )

    environment: Environment = Field()
    domain: str = Field()
    tenant_db_platform: DbPlatform = Field()

SETTINGS = Settings()