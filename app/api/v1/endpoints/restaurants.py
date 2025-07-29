from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from .... import crud, models, schemas, deps, database, utils, services

router = APIRouter()

# =================================================================
#                   Управление Профилем Ресторана
# =================================================================
@router.post("/", response_model=schemas.RestaurantPublic, status_code=status.HTTP_201_CREATED)
def create_my_restaurant(
    restaurant_in: schemas.RestaurantCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Создание профиля ресторана."""
    existing_restaurant = crud.get_restaurant_by_owner_id(db, owner_id=current_user.id)
    if existing_restaurant:
        raise HTTPException(status_code=400, detail="У вас уже есть зарегистрированный ресторан.")
    return crud.create_restaurant(db=db, restaurant=restaurant_in, owner_id=current_user.id)

@router.put("/me", response_model=schemas.RestaurantPublic)
def update_my_restaurant_profile(
    restaurant_in: schemas.RestaurantUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Обновить информацию о своем ресторане."""
    db_restaurant = current_user.owned_restaurant
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден.")
    return crud.update_restaurant_profile(db, db_restaurant=db_restaurant, restaurant_in=restaurant_in)

@router.patch("/me/status", response_model=schemas.RestaurantPublic)
def update_my_restaurant_status(
    status_in: schemas.RestaurantStatusUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Открыть или закрыть ресторан для приема заказов."""
    db_restaurant = current_user.owned_restaurant
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден.")
    return crud.update_restaurant_status(db, db_restaurant=db_restaurant, is_active=status_in.is_active)

@router.patch("/me/images", response_model=schemas.RestaurantPublic)
def upload_restaurant_images(
    logo: Optional[UploadFile] = File(None),
    banner: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Загрузить логотип и/или баннер для своего ресторана."""
    db_restaurant = current_user.owned_restaurant
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Сначала необходимо создать ресторан.")

    logo_url = utils.save_upload_file(logo) if logo else None
    banner_url = utils.save_upload_file(banner) if banner else None
    
    if not logo_url and not banner_url:
        raise HTTPException(status_code=400, detail="Необходимо загрузить хотя бы один файл.")

    return crud.update_restaurant_images(db, db_restaurant, logo_url, banner_url)

# =================================================================
#                   Управление Меню (Категории и Блюда)
# =================================================================
@router.get("/menu/categories", response_model=List[schemas.CategoryPublic])
def list_global_categories(db: Session = Depends(database.get_db)):
    """Получить список всех доступных глобальных категорий."""
    return crud.get_all_categories(db)

@router.post("/menu/dishes", response_model=schemas.DishPublic, status_code=status.HTTP_201_CREATED)
def create_dish(
    name: str = Form(...),
    price: Decimal = Form(...),
    category_id: int = Form(...),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Добавить новое блюдо в меню своего ресторана."""
    db_restaurant = current_user.owned_restaurant
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Сначала создайте ресторан.")
    
    db_category = crud.get_category_by_id(db, category_id=category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Категория не найдена.")
        
    image_url = utils.save_upload_file(image) if image else None
    dish_in = schemas.DishCreate(name=name, price=price, category_id=category_id, description=description)
    
    return crud.create_dish(db, dish=dish_in, restaurant_id=db_restaurant.id, image_url=image_url)

@router.put("/menu/dishes/{dish_id}", response_model=schemas.DishPublic)
def update_dish(
    dish_id: int,
    name: str = Form(...),
    price: Decimal = Form(...),
    description: Optional[str] = Form(None),
    is_available: bool = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Обновить информацию о блюде."""
    db_restaurant = current_user.owned_restaurant
    db_dish = crud.get_dish_by_id(db, dish_id=dish_id)
    if not db_dish or db_dish.restaurant_id != db_restaurant.id:
        raise HTTPException(status_code=404, detail="Блюдо не найдено.")

    image_url = utils.save_upload_file(image) if image else None
    dish_in = schemas.DishUpdate(name=name, price=price, description=description, is_available=is_available)
    
    return crud.update_dish(db, db_dish=db_dish, dish_in=dish_in, image_url=image_url)

@router.delete("/menu/dishes/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(
    dish_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Удалить блюдо из меню."""
    db_restaurant = current_user.owned_restaurant
    db_dish = crud.get_dish_by_id(db, dish_id=dish_id)
    if not db_dish or db_dish.restaurant_id != db_restaurant.id:
        raise HTTPException(status_code=404, detail="Блюдо не найдено.")
    crud.delete_dish(db, db_dish=db_dish)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# =================================================================
#                   Управление Заказами
# =================================================================
@router.get("/me/orders", response_model=List[schemas.OrderExtendedPublic])
def get_my_restaurant_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Получение всех заказов, принадлежащих ресторану текущего владельца."""
    if not current_user.owned_restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден.")
        
    return crud.get_orders_by_restaurant(db, restaurant_id=current_user.owned_restaurant.id)

@router.post("/me/orders/{order_id}/accept", response_model=schemas.OrderExtendedPublic)
def accept_order(
    order_id: int,
    accept_data: schemas.OrderAccept,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Принять заказ, указав время приготовления и тип доставки."""
    restaurant = current_user.owned_restaurant
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден.")
        
    db_order = crud.get_order_by_id(db, order_id=order_id)
    if not db_order or db_order.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Заказ не найден.")
    
    if db_order.status != models.OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="Можно принять только оплаченный заказ.")

    updated_order = crud.accept_order(db, db_order=db_order, accept_data=accept_data)

    if updated_order.delivery_type == models.DeliveryType.APP_COURIER:
        background_tasks.add_task(services.trigger_courier_search, order_id=updated_order.id)
        print(f"Задача по поиску курьера для заказа #{updated_order.id} добавлена в фон.")

    return updated_order

@router.post("/me/orders/{order_id}/cancel", response_model=schemas.OrderExtendedPublic)
def cancel_order(
    order_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_restaurant_owner)
):
    """Отменить заказ (доступно только до того, как его заберет курьер)."""
    restaurant = current_user.owned_restaurant
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден.")
        
    db_order = crud.get_order_by_id(db, order_id=order_id)
    if not db_order or db_order.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Заказ не найден.")
        
    cancellable_statuses = [
        models.OrderStatus.PAID,
        models.OrderStatus.ACCEPTED,
        models.OrderStatus.PREPARING,
        models.OrderStatus.AWAITING_COURIER_SEARCH,
        models.OrderStatus.READY_FOR_PICKUP,
    ]
    if db_order.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400, 
            detail="Этот заказ уже нельзя отменить, так как он в пути или был доставлен."
        )

    return crud.cancel_order_by_restaurant(db, db_order=db_order)
