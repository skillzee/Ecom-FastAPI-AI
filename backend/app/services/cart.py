from sqlmodel import Session, select

from app.models.cart import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemDetail, CartRead


class ProductNotFoundError(Exception):
    pass


class ProductOutOfStockError(Exception):
    pass


class CartQuantityLimitError(Exception):
    pass


class CartItemNotFoundError(Exception):
    pass


def get_cart(session: Session, user_id: int) -> CartRead:
    rows = session.exec(
        select(CartItem, Product)
        .outerjoin(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    ).all()
    items = [
        CartItemDetail(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            product=product,
            subtotal_paise=product.price_paise * item.quantity if product else None,
        )
        for item, product in rows
    ]
    return CartRead(
        items=items,
        total_paise=sum(item.subtotal_paise or 0 for item in items),
    )


def get_owned_item(session: Session, user_id: int, item_id: int) -> CartItem:
    item = session.exec(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
    ).first()
    if item is None:
        raise CartItemNotFoundError
    return item


def update_cart_item(
    session: Session, user_id: int, item_id: int, quantity: int
) -> CartItem:
    item = get_owned_item(session, user_id, item_id)
    product = session.get(Product, item.product_id)
    if product is None:
        raise ProductNotFoundError
    if not product.in_stock:
        raise ProductOutOfStockError
    if not 1 <= quantity <= 100:
        raise CartQuantityLimitError
    item.quantity = quantity
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def delete_cart_item(session: Session, user_id: int, item_id: int) -> None:
    item = get_owned_item(session, user_id, item_id)
    session.delete(item)
    session.commit()


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
