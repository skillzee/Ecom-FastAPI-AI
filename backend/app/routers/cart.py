from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUser, SessionDep
from app.schemas.cart import CartItemCreate, CartItemRead
from app.services import cart as cart_service


router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post("/items", response_model=CartItemRead)
def add_item(
    item_data: CartItemCreate,
    user: CurrentUser,
    session: SessionDep,
):
    try:
        return cart_service.add_cart_item(
            session=session,
            user_id=user.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
        )
    except cart_service.ProductNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        ) from None
    except cart_service.ProductOutOfStockError:
        raise HTTPException(
            status_code=409,
            detail="Product is out of stock",
        ) from None
    except cart_service.CartQuantityLimitError:
        raise HTTPException(
            status_code=409,
            detail="Maximum cart quantity is 100 per product",
        ) from None