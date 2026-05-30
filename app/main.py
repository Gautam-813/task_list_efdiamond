from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import generate_csrf_token, make_cookie_kwargs
from app.database import Base, SessionLocal, engine
from app.routers import auth, pages
from app.services.bootstrap import ensure_default_admin
from app.services.schema import ensure_schema


CSRF_COOKIE = "csrf_token"


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.cookies.get(CSRF_COOKIE):
            response.set_cookie(CSRF_COOKIE, generate_csrf_token(), **make_cookie_kwargs())
        return response


app = FastAPI(title="Shared Task Management App")
app.add_middleware(CSRFMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(pages.router)
