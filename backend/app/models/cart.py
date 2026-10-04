from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint("user_id", "product_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    product_id: int = Field(foreign_key="products.id")
    quantity: int