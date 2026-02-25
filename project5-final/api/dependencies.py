"""
dependencies.py - Зависимости FastAPI: авторизация и проверка ролей.
"""

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from .database import SessionLocal
from .auth import decode_access_token
from .models import User


# ─── Сессия БД ────────────────────────────────────────────────
def get_db():
    """Получить сессию БД (закрывается автоматически)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Текущий пользователь ─────────────────────────────────────
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Извлечь текущего пользователя из JWT-cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


# ─── Проверка ролей ───────────────────────────────────────────
def require_role(*allowed_roles: str):
    """Фабрика зависимостей: проверяет роль пользователя."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker


# ─── Шорткаты ────────────────────────────────────────────────
require_admin = require_role("admin")
require_manager = require_role("admin", "manager")
require_viewer = require_role("admin", "viewer")
require_any = require_role("admin", "manager", "viewer")