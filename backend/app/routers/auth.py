from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthUser
from app.schemas import AuthMeOut, AuthStatusOut, LoginIn
from app.security import (
    COOKIE_NAME,
    authenticate,
    check_login_rate,
    clear_session_cookie,
    client_ip,
    create_session,
    current_user,
    revoke_session,
    set_session_cookie,
    user_configured,
)

router = APIRouter()


@router.get("/auth/status", response_model=AuthStatusOut)
def auth_status(db: Session = Depends(get_db)):
    return AuthStatusOut(configured=user_configured(db))


@router.post("/auth/login", response_model=AuthMeOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    if not user_configured(db):
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Run ./set-password.sh on the server.",
        )
    check_login_rate(client_ip(request))
    user = authenticate(db, payload.username.strip(), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(db, user)
    set_session_cookie(response, token)
    return AuthMeOut(username=user.username)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_session(db, request.cookies.get(COOKIE_NAME))
    clear_session_cookie(response)


@router.get("/auth/me", response_model=AuthMeOut)
def me(user: AuthUser = Depends(current_user)):
    return AuthMeOut(username=user.username)
