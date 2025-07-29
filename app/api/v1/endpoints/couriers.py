from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from decimal import Decimal
from .... import crud, models, schemas, deps, database, utils

router = APIRouter()

# =================================================================
#                   Личный кабинет курьера
# =================================================================

@router.get("/me", response_model=schemas.CourierProfilePublic)
def get_my_profile(
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Получить информацию о своем профиле курьера.
    """
    return crud.get_or_create_courier_profile(db, user_id=current_courier.id)

@router.put("/me", response_model=schemas.CourierProfilePublic)
def update_my_profile(
    profile_in: schemas.CourierProfileUpdate,
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Обновить информацию в своем профиле (например, номер карты).
    """
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    return crud.update_courier_profile_info(db, profile=profile, profile_in=profile_in)

@router.post("/me/id_card", response_model=schemas.CourierProfilePublic)
def upload_id_card_image(
    id_card: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Загрузить фото удостоверения для верификации.
    """
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    image_url = utils.save_upload_file(id_card)
    return crud.update_courier_id_card(db, profile=profile, image_url=image_url)

@router.patch("/me/status", response_model=schemas.CourierProfilePublic)
def update_my_online_status(
    status_in: schemas.CourierStatusUpdate,
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Изменить свой статус (онлайн/оффлайн).
    """
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    if profile.verification_status != models.VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не можете выйти на линию, пока ваш профиль не будет одобрен администратором."
        )
    return crud.update_courier_online_status(db, profile=profile, is_online=status_in.is_online)

# =================================================================
#                   Работа с Заказами
# =================================================================

@router.get("/orders/available", response_model=List[schemas.OrderExtendedPublic])
def get_available_orders_for_pickup(
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Получение списка заказов, готовых к доставке.
    """
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    if not profile.is_online:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не в сети. Чтобы видеть заказы, измените свой статус на 'онлайн'."
        )
    return crud.get_available_orders_for_courier(db)


@router.post("/orders/{order_id}/accept", response_model=schemas.OrderExtendedPublic)
def accept_order_for_delivery(
    order_id: int,
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Курьер принимает заказ на доставку.
    """
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    if not profile.is_online:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не в сети.")
        
    db_order = crud.get_order_by_id(db, order_id=order_id)
    if not db_order or db_order.status != models.OrderStatus.READY_FOR_PICKUP or db_order.courier_id is not None:
        raise HTTPException(status_code=404, detail="Заказ не найден или уже взят другим курьером.")
        
    return crud.assign_order_to_courier(db, db_order, courier_id=current_courier.id)


# --- ОБНОВЛЕННЫЙ ЭНДПОИНТ ---
@router.patch("/orders/{order_id}/status", response_model=schemas.OrderExtendedPublic)
def update_courier_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """Обновление статуса заказа курьером. При статусе 'delivered' начисляет деньги на баланс."""
    db_order = crud.get_order_by_id(db, order_id=order_id)
    if not db_order or db_order.courier_id != current_courier.id:
        raise HTTPException(status_code=404, detail="Заказ не найден или не назначен вам.")
    
    allowed_statuses = [models.OrderStatus.DELIVERED, models.OrderStatus.CANCELLED]
    if status_update.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Недопустимый статус для курьера.")

    updated_order = crud.update_order_status(db, db_order, status_update.status)
    
    # Если заказ доставлен, начисляем деньги на баланс
    if updated_order.status == models.OrderStatus.DELIVERED and updated_order.delivery_fee:
        crud.add_funds_to_courier_balance(db, courier_id=current_courier.id, amount=updated_order.delivery_fee)
        print(f"Курьеру #{current_courier.id} начислено {updated_order.delivery_fee} за заказ #{updated_order.id}")

    return updated_order

# =================================================================
#                   Кошелек и Выплаты
# =================================================================
@router.post("/me/payouts", response_model=schemas.PayoutRequestPublic)
def request_payout(
    request_in: schemas.PayoutRequestCreate,
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """Создать запрос на вывод средств с баланса."""
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    try:
        return crud.create_payout_request(db, profile=profile, amount=request_in.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me/payouts", response_model=List[schemas.PayoutRequestPublic])
def get_my_payout_history(
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """Получить историю своих запросов на выплату."""
    profile = crud.get_or_create_courier_profile(db, user_id=current_courier.id)
    return crud.get_courier_payout_requests(db, profile_id=profile.id)

# =================================================================
#                   История и Заработок Курьера
# =================================================================

@router.get("/me/history", response_model=schemas.CourierEarnings)
def get_my_delivery_history(
    start_date: date = Query(default=date.today(), description="Дата начала периода (YYYY-MM-DD)"),
    end_date: date = Query(default=date.today(), description="Дата окончания периода (YYYY-MM-DD)"),
    db: Session = Depends(database.get_db),
    current_courier: models.User = Depends(deps.get_current_active_courier)
):
    """
    Получить историю выполненных заказов и заработок за период.
    По умолчанию показывает данные за сегодня.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дата начала не может быть позже даты окончания."
        )

    orders = crud.get_courier_delivered_orders(
        db, 
        courier_id=current_courier.id, 
        start_date=start_date, 
        end_date=end_date
    )
    
    total_earnings = sum([order.delivery_fee for order in orders if order.delivery_fee is not None], Decimal(0))
    
    return {
        "total_earnings": total_earnings,
        "orders_count": len(orders),
        "orders": orders
    }
