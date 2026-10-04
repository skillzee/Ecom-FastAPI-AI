from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


def register_user(session: Session, user_data: UserCreate) -> User:
    # Treat email addresses consistently for registration and future login.
    email = str(user_data.email).lower()
    statement = select(User).where(User.email == email)

    if session.exec(statement).first() is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password.get_secret_value()),
    )
    session.add(user)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Another request may have registered the email after our initial check.
        if session.exec(statement).first() is not None:
            raise EmailAlreadyRegisteredError from None
        raise

    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    statement = select(User).where(User.email == email.lower())
    user = session.exec(statement).first()
    hashed_password = user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, hashed_password)

    if user is None or not password_matches:
        return None

    return user
