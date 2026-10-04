from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.database import get_session
from app.schemas.product import Product, ProductCreate
from app.services import products as product_service


router = APIRouter(prefix="/products", tags=["Products"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[Product])
def list_products(session: SessionDep):
    return product_service.list_products(session)


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: int, session: SessionDep):
    product = product_service.get_product(session, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@router.post("", response_model=Product, status_code=201)
def create_product(
    product_data: ProductCreate,
    session: SessionDep,
):
    return product_service.create_product(session, product_data)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, session: SessionDep):
    deleted = product_service.delete_product(session, product_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return Response(status_code=204)