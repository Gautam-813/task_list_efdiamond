from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Shared Tasks"
    database_url: str = "sqlite:///./task_app.db"
    secret_key: str = "change-this-secret-before-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"


settings = Settings()

