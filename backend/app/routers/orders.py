from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUser, SessionDep
from app.schemas.order import CheckoutRequest, OrderRead
from app.services import orders as order_service


router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderRead, status_code=201)
def checkout(request: CheckoutRequest, user: CurrentUser, session: SessionDep):
    try:
        return order_service.checkout(session, user.id, request)
    except order_service.CheckoutConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get("", response_model=list[OrderRead])
def list_orders(user: CurrentUser, session: SessionDep):
    return order_service.list_orders(session, user.id)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, user: CurrentUser, session: SessionDep):
    order = order_service.get_order(session, user.id, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
