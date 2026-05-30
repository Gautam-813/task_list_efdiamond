from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import create_access_token, make_cookie_kwargs, verify_password
from app.database import get_db
from app.dependencies import CSRF_COOKIE, validate_csrf
from app.main_templates import templates
from app.models.user import User

router = APIRouter()

_login_attempts: dict[str, list[datetime]] = {}
_login_lock = Lock()


def _check_login_rate_limit(ip: str) -> None:
    from app.core.config import settings

    now = datetime.now(timezone.utc)
    window = timedelta(minutes=settings.login_rate_limit_window_minutes)
    with _login_lock:
        attempts = _login_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < window]
        _login_attempts[ip] = attempts
        if len(attempts) >= settings.login_rate_limit_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {settings.login_rate_limit_window_minutes} minutes.",
            )
        attempts.append(now)


@router.get("/login")
def login_page(request: Request):
    if request.cookies.get("access_token"):
        return RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "rate_limit": False})


@router.post("/login")
def login(
    request: Request,
    csrf_token: str = Form(""),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    try:
        _check_login_rate_limit(client_ip)
    except HTTPException:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Too many login attempts. Please wait before trying again.", "rate_limit": True},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    validate_csrf(csrf_token, request.cookies.get(CSRF_COOKIE))

    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password.", "rate_limit": False},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    with _login_lock:
        _login_attempts.pop(client_ip, None)

    response = RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        "access_token",
        create_access_token(user.username),
        max_age=60 * 60 * 8,
        **make_cookie_kwargs(),
    )
    return response


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")):
    validate_csrf(csrf_token, request.cookies.get(CSRF_COOKIE))
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

