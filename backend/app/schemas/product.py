from pydantic import BaseModel, Field, ConfigDict


class Product(BaseModel):
    id: int
    name: str
    price_paise: int
    in_stock: bool




class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_paise: int = Field(ge=0)
    in_stock: bool = True


class Product(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int