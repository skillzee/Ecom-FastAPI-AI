from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ShippingAddress(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=300)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(min_length=2, max_length=100)


class CheckoutItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)
    unit_price_paise: int = Field(ge=0)


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkout_key: UUID
    shipping: ShippingAddress
    items: list[CheckoutItem] = Field(min_length=1, max_length=200)
    expected_total_paise: int = Field(ge=0)

    @field_validator("items")
    @classmethod
    def unique_products(cls, items):
        if len({item.product_id for item in items}) != len(items):
            raise ValueError("Each product may appear only once")
        return items

    @model_validator(mode="after")
    def matching_total(self):
        if sum(item.quantity * item.unit_price_paise for item in self.items) != self.expected_total_paise:
            raise ValueError("Expected total must match the reviewed items")
        return self


class OrderItemRead(CheckoutItem):
    model_config = ConfigDict(from_attributes=True)

    name: str
    subtotal_paise: int


class OrderRead(BaseModel):
    id: int
    created_at: str
    status: str
    total_paise: int
    shipping: ShippingAddress
    items: list[OrderItemRead]
