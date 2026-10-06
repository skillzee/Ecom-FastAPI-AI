import hashlib
import json

from sqlmodel import Session, select

from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import CheckoutRequest, OrderRead, ShippingAddress


class CheckoutConflictError(Exception):
    pass


def serialize_order(session: Session, order: Order) -> OrderRead:
    items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)
    ).all()
    return OrderRead(
        id=order.id,
        created_at=order.created_at,
        status=order.status,
        total_paise=order.total_paise,
        shipping=ShippingAddress(**{field: getattr(order, field) for field in ShippingAddress.model_fields}),
        items=items,
    )


def list_orders(session: Session, user_id: int) -> list[OrderRead]:
    orders = session.exec(
        select(Order).where(Order.user_id == user_id).order_by(Order.id.desc())
    ).all()
    return [serialize_order(session, order) for order in orders]


def get_order(session: Session, user_id: int, order_id: int) -> OrderRead | None:
    order = session.exec(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    ).first()
    return serialize_order(session, order) if order else None


def checkout(session: Session, user_id: int, request: CheckoutRequest) -> OrderRead:
    payload = request.model_dump(mode="json")
    payload["items"] = sorted(payload["items"], key=lambda item: item["product_id"])
    request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    try:
        # SQLite is the project's database. Acquire its write lock before reading
        # the cart so concurrent checkouts cannot consume the same cart twice.
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        existing = session.exec(select(Order).where(
            Order.user_id == user_id, Order.checkout_key == str(request.checkout_key)
        )).first()
        if existing:
            if existing.request_hash != request_hash:
                raise CheckoutConflictError("This checkout key was already used with different details")
            result = serialize_order(session, existing)
            session.commit()
            return result

        rows = session.exec(
            select(CartItem, Product)
            .outerjoin(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id)
        ).all()
        if not rows:
            raise CheckoutConflictError("Your cart is empty")
        for item, product in rows:
            if product is None or not product.in_stock:
                raise CheckoutConflictError("Remove unavailable products from your bag before checkout")
            if not 1 <= item.quantity <= 100:
                raise CheckoutConflictError("A cart quantity is invalid; update your bag before checkout")
        current = sorted(
            [(product.id, item.quantity, product.price_paise) for item, product in rows]
        )
        reviewed = sorted(
            [(item.product_id, item.quantity, item.unit_price_paise) for item in request.items]
        )
        if current != reviewed:
            raise CheckoutConflictError("Your bag or prices changed. Review your bag and try again")
        total = sum(item.quantity * product.price_paise for item, product in rows)
        if total != request.expected_total_paise:
            raise CheckoutConflictError("Prices changed. Review your bag and try again")
        order = Order(
            user_id=user_id,
            checkout_key=str(request.checkout_key),
            request_hash=request_hash,
            total_paise=total,
            **request.shipping.model_dump(),
        )
        session.add(order)
        session.flush()
        for item, product in rows:
            session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                quantity=item.quantity,
                unit_price_paise=product.price_paise,
                subtotal_paise=product.price_paise * item.quantity,
            ))
            session.delete(item)
        session.flush()
        result = serialize_order(session, order)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
