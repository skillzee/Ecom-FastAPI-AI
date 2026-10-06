from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import Product


class CartItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0, le=100)


class CartItemDetail(CartItemRead):
    product: Product | None
    subtotal_paise: int | None


class CartRead(BaseModel):
    items: list[CartItemDetail]
    total_paise: int
