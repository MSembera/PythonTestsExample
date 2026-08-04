from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    base_url: str = "https://automationintesting.online"
    # admin/password are the intended, publicly documented demo credentials for
    # this training site (not real secrets) - safe to ship as code defaults.
    admin_username: str = "admin"
    admin_password: str = "password"


settings = Settings()
