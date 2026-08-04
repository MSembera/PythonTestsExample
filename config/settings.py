from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    base_url: str = "https://automationintesting.online"
    admin_username: str = "admin"
    admin_password: str = "password"


settings = Settings()
