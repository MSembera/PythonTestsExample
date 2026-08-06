from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    base_url: str = "https://automationintesting.online"
    # Credentials in an .env file. Copy .env.example to .env and fill in the values.
    admin_username: str
    admin_password: str


settings = Settings()
