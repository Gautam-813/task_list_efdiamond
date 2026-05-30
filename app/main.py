from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token, generate_csrf_token, make_cookie_kwargs
from app.database import Base, SessionLocal, engine
from app.routers import auth, pages
from app.services.bootstrap import ensure_default_admin
from app.services.schema import ensure_sqlite_schema


CSRF_COOKIE = "csrf_token"
UPLOAD_ROOT = Path("app/uploads")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.cookies.get(CSRF_COOKIE):
            response.set_cookie(CSRF_COOKIE, generate_csrf_token(), **make_cookie_kwargs())
        return response


app = FastAPI(title="Shared Task Management App")
app.add_middleware(CSRFMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/uploads/{task_id}/{filename}")
def serve_upload(task_id: int, filename: str, request: Request):
    token = request.cookies.get("access_token")
    username = decode_access_token(token) if token else None
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # path traversal protection
    clean_name = Path(filename).name
    file_path = UPLOAD_ROOT / str(task_id) / clean_name
    file_path = file_path.resolve()
    expected_root = UPLOAD_ROOT.resolve()
    if expected_root not in file_path.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return FileResponse(
        path=str(file_path),
        filename=clean_name,
        headers={"Content-Disposition": f"inline; filename=\"{clean_name}\""},
    )


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema(engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(pages.router)
