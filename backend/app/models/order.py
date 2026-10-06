from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("user_id", "checkout_key"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    checkout_key: str
    request_hash: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending_payment"
    total_paise: int
    full_name: str
    address: str
    city: str
    postal_code: str
    country: str


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    # Keep snapshots even when a catalog product is changed or deleted.
    product_id: int
    name: str
    quantity: int
    unit_price_paise: int
    subtotal_paise: int
