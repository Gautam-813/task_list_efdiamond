from jinja2 import Environment, FileSystemLoader
from starlette.templating import Jinja2Templates

from app.core.config import settings


_env = Environment(
    loader=FileSystemLoader("app/templates"),
    cache_size=0 if settings.environment == "production" else 50,
)
templates = Jinja2Templates(env=_env)

