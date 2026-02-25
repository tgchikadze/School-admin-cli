"""
routers/auth.py - Эндпоинты авторизации: login, register, me, logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password, create_access_token
from ..dependencies import get_db, get_current_user
from ..models import User

router = APIRouter(tags=["auth"])


@router.post("/api/register/json")
async def register_json(request: Request, db: Session = Depends(get_db)):
    """Регистрация через JSON body."""
    data = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "manager")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    # Первый пользователь = admin
    if db.query(User).count() == 0:
        role = "admin"

    if role not in ("admin", "manager", "viewer"):
        role = "manager"

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
        full_name=full_name or username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "username": user.username, "role": user.role, "full_name": user.full_name}


@router.post("/api/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Вход: проверяет credentials, ставит JWT в cookie."""
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        username = form.get("username", "").strip()
        password = form.get("password", "")
    else:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(data={"sub": user.username, "role": user.role})

    if "application/x-www-form-urlencoded" in content_type:
        resp = RedirectResponse(url="/", status_code=302)
    else:
        resp = Response(content='{"detail":"Login successful"}', media_type="application/json")

    resp.set_cookie(key="access_token", value=token, httponly=True, samesite="lax", max_age=60*60*24)
    return resp


@router.get("/api/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username,
            "role": current_user.role, "full_name": current_user.full_name}


@router.post("/api/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    from fastapi.templating import Jinja2Templates
    import os
    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "web", "templates"
    )
    templates = Jinja2Templates(directory=templates_dir)
    return templates.TemplateResponse("login.html", {"request": request})