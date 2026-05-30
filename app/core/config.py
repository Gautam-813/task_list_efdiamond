from os import getenv

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Shared Tasks"
    database_url: str = "sqlite:///./task_app.db"
    secret_key: str = "change-this-secret-before-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"
    environment: str = "development"
    max_upload_size_mb: int = 10
    password_min_length: int = 8
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_minutes: int = 15
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

PRODUCTION = settings.environment == "production"

