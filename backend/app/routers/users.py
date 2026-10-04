from fastapi import APIRouter

from app.core.dependencies import CurrentUser
from app.schemas.user import UserRead


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_current_user(user: CurrentUser):
    return user
