from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, SessionLocal, engine
from app.routers import auth, pages
from app.services.bootstrap import ensure_default_admin
from app.services.schema import ensure_sqlite_schema


app = FastAPI(title="Shared Task Management App")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")


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
