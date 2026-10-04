from sqlmodel import Session, select

from app.models.cart import CartItem
from app.models.product import Product


class ProductNotFoundError(Exception):
    pass


class ProductOutOfStockError(Exception):
    pass


class CartQuantityLimitError(Exception):
    pass


def add_cart_item(
    session: Session,
    user_id: int,
    product_id: int,
    quantity: int,
) -> CartItem:
    product = session.get(Product, product_id)

    if product is None:
        raise ProductNotFoundError

    if not product.in_stock:
        raise ProductOutOfStockError

    statement = select(CartItem).where(
        CartItem.user_id == user_id,
        CartItem.product_id == product_id,
    )
    cart_item = session.exec(statement).first()

    new_quantity = quantity
    if cart_item is not None:
        new_quantity += cart_item.quantity

    if new_quantity > 100:
        raise CartQuantityLimitError

    if cart_item is None:
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=new_quantity,
        )
    else:
        cart_item.quantity = new_quantity

    session.add(cart_item)
    session.commit()
    session.refresh(cart_item)

    return cart_item