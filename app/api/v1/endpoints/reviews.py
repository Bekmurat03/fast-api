from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .... import crud, models, schemas, deps, database

router = APIRouter()

@router.post("/order/{order_id}", response_model=schemas.ReviewPublic, status_code=status.HTTP_201_CREATED)
def create_review_for_order(
    order_id: int,
    review_in: schemas.ReviewCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Оставить отзыв на заказ."""
    order = crud.get_order_by_id(db, order_id=order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден.")
    if order.status != models.OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Можно оставить отзыв только на завершенный заказ.")
    if order.review:
        raise HTTPException(status_code=400, detail="Вы уже оставили отзыв на этот заказ.")

    return crud.create_review(
        db, 
        review=review_in, 
        order_id=order_id, 
        user_id=current_user.id, 
        restaurant_id=order.restaurant_id
    )
