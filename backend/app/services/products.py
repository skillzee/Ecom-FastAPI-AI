from sqlmodel import Session, select

from app.models.product import Product as ProductRecord
from app.schemas.product import ProductCreate


def list_products(session: Session) -> list[ProductRecord]:
    statement = select(ProductRecord)
    return list(session.exec(statement).all())


def get_product(
    session: Session,
    product_id: int,
) -> ProductRecord | None:
    return session.get(ProductRecord, product_id)


def create_product(session: Session, product_data: ProductCreate,) -> ProductRecord:
    product = ProductRecord(**product_data.model_dump())

    session.add(product)
    session.commit()
    session.refresh(product)

    return product


def delete_product(session: Session, product_id: int) -> bool:
    product = session.get(ProductRecord, product_id)

    if product is None:
        return False

    session.delete(product)
    session.commit()

    return True