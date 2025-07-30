from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc 
from datetime import date, datetime, timedelta, timezone
from typing import List, Union, Optional
from . import models, schemas, security, utils

# =================================================================
#                   Управление Пользователями
# =================================================================

def get_user_by_phone(db: Session, phone: str):
    return db.query(models.User).filter(models.User.phone == phone).first()

# --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ---
def create_user(db: Session, user: Union[schemas.UserPublicRegister, schemas.AdminUserCreate]):
    """
    Создает нового пользователя.
    Если роль 'restaurant', автоматически создает для него профиль ресторана.
    """
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        phone=user.phone, 
        first_name=user.first_name, 
        hashed_password=hashed_password,
        role=user.role
    )
    if user.role == models.UserRole.ADMIN:
        db_user.is_superuser = True
        
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # --- НОВАЯ ЛОГИКА ---
    # Если создается ресторан, автоматически создаем для него профиль.
    # Владелец сможет отредактировать детали позже, но админ увидит его сразу.
    if user.role == models.UserRole.RESTAURANT:
        db_restaurant = models.Restaurant(
            owner_id=db_user.id,
            name=f"Ресторан {db_user.first_name}", # Имя по умолчанию
            address="Адрес не указан",             # Адрес по умолчанию
            description="Описание пока не добавлено" # <-- ДОБАВЛЕНО: Описание по умолчанию
        )
        db.add(db_restaurant)
        db.commit()
        db.refresh(db_restaurant)

    return db_user

def get_user_by_id(db: Session, user_id: int):
    """Получить пользователя по ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """Получить список всех пользователей."""
    return db.query(models.User).offset(skip).limit(limit).all()

def update_user_status(db: Session, db_user: models.User, is_active: bool):
    """Обновить статус активности пользователя (блокировка/разблокировка)."""
    db_user.is_active = is_active
    db.commit()
    db.refresh(db_user)
    return db_user

# ... (остальные CRUD функции остаются без изменений) ...
# (Полный код файла crud.py для надежности)

def create_user_address(db: Session, address: schemas.AddressCreate, user_id: int):
    db_address = models.Address(**address.model_dump(), user_id=user_id)
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

def get_user_addresses(db: Session, user_id: int):
    return db.query(models.Address).filter(models.Address.user_id == user_id).all()

def get_address_by_id(db: Session, address_id: int):
    return db.query(models.Address).filter(models.Address.id == address_id).first()

def delete_address(db: Session, db_address: models.Address):
    db.delete(db_address)
    db.commit()

def get_active_restaurants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Restaurant).filter(
        models.Restaurant.is_approved == True, 
        models.Restaurant.is_active == True
    ).offset(skip).limit(limit).all()

def get_restaurant_details(db: Session, restaurant_id: int):
    return db.query(models.Restaurant).options(
        joinedload(models.Restaurant.dishes).joinedload(models.Dish.category)
    ).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.is_approved == True, 
        models.Restaurant.is_active == True
    ).first()

def create_restaurant(db: Session, restaurant: schemas.RestaurantCreate, owner_id: int):
    db_restaurant = models.Restaurant(**restaurant.model_dump(), owner_id=owner_id)
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def get_restaurant_by_owner_id(db: Session, owner_id: int):
    return db.query(models.Restaurant).filter(models.Restaurant.owner_id == owner_id).first()

def get_all_restaurants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Restaurant).offset(skip).limit(limit).all()

def get_restaurant_by_id(db: Session, restaurant_id: int):
    return db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()

def update_restaurant_approval(db: Session, db_restaurant: models.Restaurant, is_approved: bool):
    db_restaurant.is_approved = is_approved
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def update_restaurant_profile(db: Session, db_restaurant: models.Restaurant, restaurant_in: schemas.RestaurantUpdate):
    update_data = restaurant_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_restaurant, key, value)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def update_restaurant_status(db: Session, db_restaurant: models.Restaurant, is_active: bool):
    db_restaurant.is_active = is_active
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def update_restaurant_images(db: Session, db_restaurant: models.Restaurant, logo_url: str | None, banner_url: str | None):
    if logo_url:
        utils.delete_file(db_restaurant.logo)
        db_restaurant.logo = logo_url
    if banner_url:
        utils.delete_file(db_restaurant.banner)
        db_restaurant.banner = banner_url
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def create_category(db: Session, category: schemas.CategoryCreate, image_url: Optional[str] = None):
    db_category = models.Category(name=category.name, image_url=image_url)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def get_all_categories(db: Session):
    return db.query(models.Category).all()

def get_category_by_id(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id).first()

def delete_category(db: Session, db_category: models.Category):
    utils.delete_file(db_category.image_url)
    db.delete(db_category)
    db.commit()

def create_dish(db: Session, dish: schemas.DishCreate, restaurant_id: int, image_url: Optional[str] = None):
    db_dish = models.Dish(
        **dish.model_dump(),
        restaurant_id=restaurant_id,
        image=image_url
    )
    db.add(db_dish)
    db.commit()
    db.refresh(db_dish)
    return db_dish
    
def get_dish_by_id(db: Session, dish_id: int):
    return db.query(models.Dish).filter(models.Dish.id == dish_id).first()

def update_dish(db: Session, db_dish: models.Dish, dish_in: schemas.DishUpdate, image_url: Optional[str] = None):
    update_data = dish_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_dish, key, value)
    if image_url:
        utils.delete_file(db_dish.image)
        db_dish.image = image_url
    db.commit()
    db.refresh(db_dish)
    return db_dish

def delete_dish(db: Session, db_dish: models.Dish):
    utils.delete_file(db_dish.image)
    db.delete(db_dish)
    db.commit()

def get_order_by_id(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders_by_restaurant(db: Session, restaurant_id: int):
    return db.query(models.Order).filter(models.Order.restaurant_id == restaurant_id).order_by(models.Order.created_at.desc()).all()

def accept_order(db: Session, db_order: models.Order, accept_data: schemas.OrderAccept) -> models.Order:
    db_order.delivery_type = accept_data.delivery_type
    db_order.preparation_time_minutes = accept_data.preparation_time_minutes
    now_utc = datetime.now(timezone.utc)
    ready_by = now_utc + timedelta(minutes=accept_data.preparation_time_minutes)
    db_order.ready_by_timestamp = ready_by
    if accept_data.delivery_type == models.DeliveryType.APP_COURIER:
        db_order.status = models.OrderStatus.AWAITING_COURIER_SEARCH
    else:
        db_order.status = models.OrderStatus.PREPARING
    db.commit()
    db.refresh(db_order)
    return db_order

def set_order_status_to_ready(db: Session, order_id: int) -> models.Order | None:
    db_order = get_order_by_id(db, order_id)
    if db_order and db_order.status == models.OrderStatus.AWAITING_COURIER_SEARCH:
        db_order.status = models.OrderStatus.READY_FOR_PICKUP
        db.commit()
        db.refresh(db_order)
        print(f"ЗАКАЗ #{db_order.id} ГОТОВ! НАЧИНАЕМ ПОИСК КУРЬЕРА.")
        return db_order
    return None

def cancel_order_by_restaurant(db: Session, db_order: models.Order) -> models.Order:
    print(f"ИНИЦИИРОВАН ВОЗВРАТ СРЕДСТВ ДЛЯ ЗАКАЗА #{db_order.id}")
    db_order.status = models.OrderStatus.CANCELLED
    db.commit()
    db.refresh(db_order)
    return db_order

def mark_order_as_paid(db: Session, order_id: int):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order and db_order.status == models.OrderStatus.PENDING:
        db_order.status = models.OrderStatus.PAID
        db.commit()
        db.refresh(db_order)
    return db_order

def get_available_orders_for_courier(db: Session):
    return db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.READY_FOR_PICKUP,
        models.Order.courier_id == None
    ).order_by(models.Order.created_at.asc()).all()

def assign_order_to_courier(db: Session, db_order: models.Order, courier_id: int):
    db_order.courier_id = courier_id
    db_order.status = models.OrderStatus.ON_THE_WAY
    db.commit()
    db.refresh(db_order)
    return db_order

def get_courier_delivered_orders(db: Session, courier_id: int, start_date: date, end_date: date):
    end_datetime = datetime.combine(end_date, datetime.max.time())
    return db.query(models.Order).filter(
        models.Order.courier_id == courier_id,
        models.Order.status == models.OrderStatus.DELIVERED,
        models.Order.created_at >= start_date,
        models.Order.created_at <= end_datetime
    ).order_by(models.Order.created_at.desc()).all()

def get_or_create_courier_profile(db: Session, user_id: int) -> models.CourierProfile:
    profile = db.query(models.CourierProfile).filter(models.CourierProfile.user_id == user_id).first()
    if not profile:
        profile = models.CourierProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

def update_courier_profile_info(db: Session, profile: models.CourierProfile, profile_in: schemas.CourierProfileUpdate):
    profile.card_number = profile_in.card_number
    db.commit()
    db.refresh(profile)
    return profile

def update_courier_id_card(db: Session, profile: models.CourierProfile, image_url: str):
    if profile.id_card_image_url:
        utils.delete_file(profile.id_card_image_url)
    profile.id_card_image_url = image_url
    profile.verification_status = models.VerificationStatus.ON_REVIEW
    db.commit()
    db.refresh(profile)
    return profile

def update_courier_online_status(db: Session, profile: models.CourierProfile, is_online: bool):
    profile.is_online = is_online
    db.commit()
    db.refresh(profile)
    return profile

def get_couriers_for_verification(db: Session):
    return db.query(models.User).join(models.CourierProfile).filter(
        models.User.role == models.UserRole.COURIER,
        models.CourierProfile.verification_status == models.VerificationStatus.ON_REVIEW
    ).options(joinedload(models.User.courier_profile)).all()

def update_courier_verification_status(db: Session, profile: models.CourierProfile, status: models.VerificationStatus):
    profile.verification_status = status
    db.commit()
    db.refresh(profile)
    return profile

def create_review(db: Session, review: schemas.ReviewCreate, order_id: int, user_id: int, restaurant_id: int):
    db_review = models.Review(**review.model_dump(), order_id=order_id, user_id=user_id, restaurant_id=restaurant_id)
    db.add(db_review)
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    new_rating = db.query(func.coalesce(func.avg(models.Review.rating), 0)).filter(models.Review.restaurant_id == restaurant_id).scalar()
    new_count = db.query(func.count(models.Review.id)).filter(models.Review.restaurant_id == restaurant_id).scalar()
    restaurant.average_rating = new_rating
    restaurant.review_count = new_count
    db.commit()
    db.refresh(db_review)
    return db_review

def get_valid_promo_code(db: Session, code: str):
    today = date.today()
    return db.query(models.PromoCode).filter(
        models.PromoCode.code == code,
        models.PromoCode.is_active == True,
        models.PromoCode.valid_from <= today,
        models.PromoCode.valid_to >= today,
        models.PromoCode.times_used < models.PromoCode.max_uses
    ).first()

def create_promo_code(db: Session, promo_code: schemas.PromoCodeCreate):
    db_promo_code = models.PromoCode(**promo_code.model_dump())
    db.add(db_promo_code)
    db.commit()
    db.refresh(db_promo_code)
    return db_promo_code

def get_all_promo_codes(db: Session):
    return db.query(models.PromoCode).all()

def get_promo_code_by_id(db: Session, promo_code_id: int):
    return db.query(models.PromoCode).filter(models.PromoCode.id == promo_code_id).first()

def update_promo_code(db: Session, db_promo_code: models.PromoCode, promo_code_in: schemas.PromoCodeUpdate):
    update_data = promo_code_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_promo_code, key, value)
    db.commit()
    db.refresh(db_promo_code)
    return db_promo_code

def delete_promo_code(db: Session, db_promo_code: models.PromoCode):
    db.delete(db_promo_code)
    db.commit()

def create_banner(db: Session, banner: schemas.BannerCreate, image_url: str):
    db_banner = models.Banner(title=banner.title, restaurant_id=banner.restaurant_id, image_url=image_url)
    db.add(db_banner)
    db.commit()
    db.refresh(db_banner)
    return db_banner

def get_active_banners(db: Session):
    return db.query(models.Banner).filter(models.Banner.is_active == True).all()

def get_banner_by_id(db: Session, banner_id: int):
    return db.query(models.Banner).filter(models.Banner.id == banner_id).first()

def delete_banner(db: Session, db_banner: models.Banner):
    image_path_to_delete = db_banner.image_url
    db.delete(db_banner)
    db.commit()
    utils.delete_file(image_path_to_delete)

def get_system_settings(db: Session) -> models.SystemSettings:
    db_settings = db.query(models.SystemSettings).first()
    if not db_settings:
        db_settings = models.SystemSettings()
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
    return db_settings

def update_system_settings(db: Session, settings_in: schemas.SystemSettingsUpdate) -> models.SystemSettings:
    db_settings = get_system_settings(db)
    for key, value in settings_in.model_dump().items():
        setattr(db_settings, key, value)
    db.commit()
    db.refresh(db_settings)
    return db_settings

def get_dashboard_stats(db: Session, start_date: date, end_date: date):
    end_datetime = datetime.combine(end_date, datetime.max.time())

    delivered_orders_query = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.DELIVERED,
        models.Order.created_at >= start_date,
        models.Order.created_at <= end_datetime
    )
    
    total_revenue = delivered_orders_query.with_entities(func.sum(models.Order.total_price)).scalar() or 0
    total_orders = delivered_orders_query.count()
    
    new_users = db.query(models.User).filter(
        models.User.date_joined >= start_date,
        models.User.date_joined <= end_datetime
    ).count()

    general_stats = schemas.GeneralStats(
        total_revenue=total_revenue,
        total_orders=total_orders,
        new_users=new_users
    )

    top_restaurants_query = db.query(
        models.Restaurant.id,
        models.Restaurant.name,
        func.count(models.Order.id).label("order_count"),
        func.sum(models.Order.total_price).label("total_revenue")
    ).join(models.Order, models.Restaurant.id == models.Order.restaurant_id).filter(
        models.Order.status == models.OrderStatus.DELIVERED,
        models.Order.created_at >= start_date,
        models.Order.created_at <= end_datetime
    ).group_by(models.Restaurant.id).order_by(desc("total_revenue")).limit(5).all()
    
    top_restaurants = [schemas.TopRestaurant.model_validate(r, from_attributes=True) for r in top_restaurants_query]

    top_couriers_query = db.query(
        models.User.id,
        models.User.first_name,
        func.count(models.Order.id).label("deliveries_count"),
        func.sum(models.Order.delivery_fee).label("total_earnings")
    ).join(models.Order, models.User.id == models.Order.courier_id).filter(
        models.Order.status == models.OrderStatus.DELIVERED,
        models.Order.created_at >= start_date,
        models.Order.created_at <= end_datetime
    ).group_by(models.User.id).order_by(desc("total_earnings")).limit(5).all()

    top_couriers = [schemas.TopCourier.model_validate(c, from_attributes=True) for c in top_couriers_query]

    top_clients_query = db.query(
        models.User.id,
        models.User.first_name,
        models.User.phone,
        func.count(models.Order.id).label("orders_count"),
        func.sum(models.Order.total_price).label("total_spent")
    ).join(models.Order, models.User.id == models.Order.user_id).filter(
        models.Order.status == models.OrderStatus.DELIVERED,
        models.Order.created_at >= start_date,
        models.Order.created_at <= end_datetime
    ).group_by(models.User.id).order_by(desc("total_spent")).limit(5).all()

    top_clients = [schemas.TopClient.model_validate(c, from_attributes=True) for c in top_clients_query]

    return schemas.DashboardData(
        general_stats=general_stats,
        top_restaurants=top_restaurants,
        top_couriers=top_couriers,
        top_clients=top_clients
    )
def get_categories(db: Session) -> List[models.Category]:
    return db.query(models.Category).all()
def update_banner(db: Session, db_banner: models.Banner, banner_in: schemas.BannerUpdate, image_url: Optional[str] = None):
    db_banner.title = banner_in.title
    db_banner.restaurant_id = banner_in.restaurant_id
    if image_url:
        utils.delete_file(db_banner.image_url)
        db_banner.image_url = image_url
    db.commit()
    db.refresh(db_banner)
    return 
def get_pending_payout_requests(db: Session):
    return db.query(models.PayoutRequest).filter(models.PayoutRequest.status == "pending").all()
def get_user_by_phone(db: Session, phone: str):
    return db.query(models.User).filter(models.User.phone == phone).first()