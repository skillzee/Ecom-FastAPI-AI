from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.database import get_session
from app.core.config import get_auth_settings
from app.core.security import create_access_token
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.users import EmailAlreadyRegisteredError, authenticate_user, register_user


router = APIRouter(prefix="/auth", tags=["Auth"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, session: SessionDep):
    try:
        return register_user(session, user_data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, session: SessionDep, response: Response):
    user = authenticate_user(
        session,
        str(user_data.email),
        user_data.password.get_secret_value(),
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_auth_settings()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )
