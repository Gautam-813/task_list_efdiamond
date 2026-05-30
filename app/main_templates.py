from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates", cache_size=0)
