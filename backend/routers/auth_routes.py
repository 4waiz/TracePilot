"""Authentication routes: login and current-user info."""

import time
from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.auth import verify_password, create_access_token, get_current_user
from backend.audit import create_audit_log
from backend.config import settings
from backend.schemas import UserOut, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiter: {ip: [timestamp, ...]}
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if the IP has exceeded the login attempt limit."""
    now = time.monotonic()
    window = settings.LOGIN_RATE_WINDOW_SECONDS
    # Prune old attempts
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < window]
    if len(_login_attempts[ip]) >= settings.LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    _login_attempts[ip].append(now)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
    )

    create_audit_log(
        db,
        user_id=user.id,
        username=user.username,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        details="User logged in",
    )

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
