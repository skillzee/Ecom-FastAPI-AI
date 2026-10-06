from fastapi import APIRouter, HTTPException, Response

from app.core.dependencies import CurrentUser, SessionDep
from app.schemas.cart import CartItemCreate, CartItemRead, CartItemUpdate, CartRead
from app.services import cart as cart_service


router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartRead)
def get_cart(user: CurrentUser, session: SessionDep):
    return cart_service.get_cart(session, user.id)


@router.patch("/items/{item_id}", response_model=CartItemRead)
def update_item(
    item_id: int, item_data: CartItemUpdate, user: CurrentUser, session: SessionDep
):
    try:
        return cart_service.update_cart_item(
            session, user.id, item_id, item_data.quantity
        )
    except cart_service.CartItemNotFoundError:
        raise HTTPException(status_code=404, detail="Cart item not found") from None
    except cart_service.ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Product not found") from None
    except cart_service.ProductOutOfStockError:
        raise HTTPException(status_code=409, detail="Product is out of stock") from None
    except cart_service.CartQuantityLimitError:
        raise HTTPException(
            status_code=409, detail="Maximum cart quantity is 100 per product"
        ) from None


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, user: CurrentUser, session: SessionDep):
    try:
        cart_service.delete_cart_item(session, user.id, item_id)
    except cart_service.CartItemNotFoundError:
        raise HTTPException(status_code=404, detail="Cart item not found") from None
    return Response(status_code=204)


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
