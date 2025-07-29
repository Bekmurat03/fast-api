import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .... import models, schemas, crud, deps, services, database

router = APIRouter()

@router.post("/", response_model=schemas.CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_with_split_payment(
    order_in: schemas.OrderCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Создание нового заказа с автоматическим разделением (сплитованием) платежа.
    """
    # 1. Проверяем ресторан и его платежные данные
    restaurant = crud.get_restaurant_by_id(db, restaurant_id=order_in.restaurant_id)
    if not restaurant or not restaurant.is_active or not restaurant.is_approved:
        raise HTTPException(status_code=404, detail="Ресторан не найден или временно недоступен.")
    if not restaurant.paylink_account_id:
        raise HTTPException(status_code=400, detail="У ресторана не настроены платежные данные для приема оплаты.")

    # 2. Проверяем адрес и зону доставки
    address = db.query(models.Address).filter(models.Address.id == order_in.address_id).first()
    if not address or address.user_id != current_user.id:
         raise HTTPException(status_code=404, detail="Адрес не найден.")
    if not services.is_address_in_delivery_zone(db, address):
        raise HTTPException(
            status_code=400, 
            detail="К сожалению, доставка по этому адресу невозможна."
        )

    # 3. Рассчитываем стоимость
    try:
        costs = services.calculate_order_costs(db, order_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
         
    # 4. Создаем заказ в базе данных
    db_order = models.Order(
        code=f"JET-{secrets.token_hex(4).upper()}",
        user_id=current_user.id,
        restaurant_id=order_in.restaurant_id,
        address_text=f"{address.city}, {address.street}, {address.house_number}",
        delivery_lat=address.latitude,
        delivery_lon=address.longitude,
        **costs
    )
    db.add(db_order)
    db.commit()
    
    for item in order_in.items:
        dish = db.query(models.Dish).get(item.dish_id)
        if dish:
            db_item = models.OrderItem(
                order_id=db_order.id,
                dish_id=item.dish_id,
                quantity=item.quantity,
                price_at_time_of_order=dish.price
            )
            db.add(db_item)
    
    db.commit()
    db.refresh(db_order)
    
    # 5. Создаем сплит-платеж через PayLink
    paylink_service = services.PayLinkService()
    payment_url = await paylink_service.create_split_payment(
        order=db_order,
        restaurant_account_id=restaurant.paylink_account_id,
        platform_account_id=services.settings.PLATFORM_PAYLINK_ACCOUNT_ID
    )
    
    if not payment_url:
        # В продакшене здесь нужна логика отката создания заказа
        raise HTTPException(status_code=502, detail="Не удалось создать ссылку на оплату. Попробуйте позже.")
    
    db_order.payment_invoice_id = payment_url.split('/')[-1]
    db.commit()
    
    return {"order_id": db_order.id, "payment_url": payment_url}
