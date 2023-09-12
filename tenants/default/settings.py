from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='settings.env',
        env_prefix='condado_'
    )

    environment: str
    domain: str

SETTINGS = Settings()