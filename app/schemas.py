from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from .models import PayoutStatus, UserRole, OrderStatus, PromoCodeType, VerificationStatus,DeliveryType

# ==================================
#         Базовые схемы
# ==================================
class Message(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    phone: Optional[str] = None

# ==================================
#         Схемы для Баннеров
# ==================================
class BannerCreate(BaseModel):
    title: str
    restaurant_id: Optional[int] = None

class BannerPublic(BaseModel):
    id: int
    title: str
    image_url: str
    restaurant_id: Optional[int] = None
    class Config:
        from_attributes = True
class BannerUpdate(BaseModel):
    title: str
    restaurant_id: Optional[int] = None
# ==================================
#         Пользователь и Адрес
# ==================================
class UserBase(BaseModel):
    phone: str = Field(..., example="77001234567")
    first_name: str = Field(..., example="Ерболат")

class UserPublicRegister(UserBase):
    """Схема для публичной регистрации клиентов и курьеров."""
    password: str = Field(..., min_length=8)
    role: UserRole

    @validator('role')
    def role_must_be_client_or_courier(cls, v):
        if v not in [UserRole.CLIENT, UserRole.COURIER]:
            raise ValueError('Регистрация доступна только для клиентов и курьеров.')
        return v

class AdminUserCreate(UserBase):
    """Схема для создания пользователей (ресторанов/админов) через админку."""
    password: str = Field(..., min_length=8)
    role: UserRole

    @validator('role')
    def role_must_be_restaurant_or_admin(cls, v):
        if v not in [UserRole.RESTAURANT, UserRole.ADMIN]:
            raise ValueError('Администратор может создавать только аккаунты ресторанов или других администраторов.')
        return v

class UserPublic(BaseModel):
    id: int
    phone: str
    first_name: str
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

class AddressBase(BaseModel):
    city: str = Field(default="Zhanaozen")
    street: str
    house_number: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
class AddressCreate(AddressBase):
    pass

class AddressPublic(AddressBase):
    id: int
    class Config:
        from_attributes = True
        
# ==================================
#         Ресторан
# ==================================
class RestaurantCreate(BaseModel):
    name: str = Field(..., example="Асхана No1")
    description: str = Field(..., example="Лучшие манты в городе")
    address: str = Field(..., example="мкр. 5, дом 20")
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RestaurantPublic(RestaurantCreate):
    id: int
    owner_id: int
    is_approved: bool
    is_active: bool
    average_rating: Decimal
    review_count: int
    logo: Optional[str] = None
    banner: Optional[str] = None
    paylink_account_id: Optional[str] = None 
    class Config:
        from_attributes = True
class OrderAccept(BaseModel):
    preparation_time_minutes: int
    delivery_type: DeliveryType

    @validator('preparation_time_minutes')
    def preparation_time_must_be_valid(cls, v):
        allowed_times = [10, 15, 20, 30]
        if v not in allowed_times:
            raise ValueError(f'Время приготовления должно быть одним из: {allowed_times}')
        return v
class RestaurantForList(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    average_rating: Decimal
    class Config:
        from_attributes = True
class RestaurantProfileUpdate(BaseModel):
    """Схема для обновления текстовой информации о ресторане."""
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None

class RestaurantPayoutDetailsUpdate(BaseModel):
    """Схема для обновления платежных данных ресторана."""
    paylink_account_id: str
class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None

class RestaurantStatusUpdate(BaseModel):
    is_active: bool

class DishForMenu(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    image: Optional[str] = None
    is_available: bool
    class Config:
        from_attributes = True

class MenuCategoryWithDishes(BaseModel):
    id: int
    name: str
    dishes: List[DishForMenu]
    class Config:
        from_attributes = True
        
class RestaurantPublicDetail(RestaurantForList):
    description: Optional[str] = None
    address: Optional[str] = None
    review_count: int
    banner: Optional[str] = None
    menu_categories: List[MenuCategoryWithDishes]
    class Config:
        from_attributes = True
# ==================================
#         Отзывы
# ==================================
class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewPublic(ReviewCreate):
    id: int
    user_id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ==================================
#         Промокоды
# ==================================
class PromoCodeApply(BaseModel):
    code: str
# ==================================
#         Схемы для Промокодов (для Админа)
# ==================================
class PromoCodeBase(BaseModel):
    code: str = Field(..., description="Уникальный код промокода (например, SALE25)")
    promo_type: PromoCodeType
    value: Decimal = Field(..., gt=0, description="Значение (процент или сумма)")
    is_active: bool = True
    valid_from: date = Field(..., description="Дата начала действия")
    valid_to: date = Field(..., description="Дата окончания действия")
    max_uses: int = Field(..., gt=0, description="Максимальное количество использований")

class PromoCodeCreate(PromoCodeBase):
    pass

class PromoCodeUpdate(PromoCodeBase):
    pass

class PromoCodePublic(PromoCodeBase):
    id: int
    times_used: int
    class Config:
        from_attributes = True
# ==================================
#         Заказ
# ==================================
class OrderItemCreate(BaseModel):
    dish_id: int
    quantity: int = Field(..., gt=0)

class OrderCreate(BaseModel):
    restaurant_id: int
    address_id: int
    items: List[OrderItemCreate]
    promo_code: Optional[str] = None

class OrderItemPublic(BaseModel):
    quantity: int
    price_at_time_of_order: Decimal
    class Config:
        from_attributes = True

class OrderPublic(BaseModel):
    id: int
    code: str
    status: OrderStatus
    total_price: Decimal
    created_at: datetime
    items: List[OrderItemPublic]
    class Config:
        from_attributes = True

class UserInOrder(BaseModel):
    first_name: str
    phone: str
    class Config:
        from_attributes = True

class OrderExtendedPublic(BaseModel):
    id: int
    code: str
    status: OrderStatus
    total_price: Decimal
    address_text: str
    created_at: datetime
    items: List[OrderItemPublic]
    user: UserInOrder
    class Config:
        from_attributes = True

# ==================================
#         Оплата
# ==================================
class CreateOrderResponse(BaseModel):
    order_id: int
    payment_url: str

# ==================================
#         Админ и Статусы
# ==================================
class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class RestaurantApprovalUpdate(BaseModel):
    is_approved: bool

class SystemSettingsBase(BaseModel):
    # Тарифы
    day_base_rate: Decimal
    day_rate_per_km: Decimal
    night_base_rate: Decimal
    night_rate_per_km: Decimal
    night_tariff_start_hour: int = Field(..., ge=0, le=23)
    night_tariff_end_hour: int = Field(..., ge=0, le=23)
    # Зона доставки
    city_center_lat: float
    city_center_lon: float
    delivery_radius_km: float = Field(..., gt=0)

class SystemSettingsPublic(SystemSettingsBase):
    id: int
    class Config:
        from_attributes = True

class SystemSettingsUpdate(SystemSettingsBase):
    pass

# ==================================
#         Схемы для Категорий и Блюд
# ==================================
class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryPublic(CategoryBase):
    id: int
    image_url: Optional[str] = None
    class Config:
        from_attributes = True

class DishBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    is_available: bool = True

class DishCreate(DishBase):
    category_id: int

class DishUpdate(DishBase):
    pass

class DishPublic(DishBase):
    id: int
    category_id: int
    image: Optional[str] = None
    class Config:
        from_attributes = True
# ==================================
#         Схемы для Курьера
# ==================================
class CourierProfileUpdate(BaseModel):
    card_number: str = Field(..., description="Номер банковской карты для выплат")

class CourierProfilePublic(BaseModel):
    user_id: int
    verification_status: VerificationStatus
    is_online: bool
    id_card_image_url: Optional[str] = None
    card_number: Optional[str] = None
    balance: Decimal # <-- Добавлено поле баланса
    
    class Config:
        from_attributes = True

class PayoutRequestCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Сумма для вывода")

class PayoutRequestPublic(BaseModel):
    id: int
    amount: Decimal
    card_number: str
    status: PayoutStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CourierStatusUpdate(BaseModel):
    is_online: bool

class OrderForCourierHistory(BaseModel):
    id: int
    code: str
    delivery_fee: Decimal # Это и есть заработок курьера с заказа
    created_at: datetime
    
    class Config:
        from_attributes = True

class CourierEarnings(BaseModel):
    total_earnings: Decimal
    orders_count: int
    orders: List[OrderForCourierHistory]
# ==================================
#         Схемы для Админа (дополнено)
# ==================================
class AdminCourierVerificationUpdate(BaseModel):
    verification_status: VerificationStatus

    @validator('verification_status')
    def status_must_be_valid(cls, v):
        # Админ может только одобрить или отклонить
        allowed_statuses = [VerificationStatus.APPROVED, VerificationStatus.REJECTED]
        if v not in allowed_statuses:
            raise ValueError(f'Статус должен быть одним из: {allowed_statuses}')
        return v

class CourierForAdmin(UserPublic):
    courier_profile: Optional[CourierProfilePublic] = None
class UserStatusUpdate(BaseModel):
    is_active: bool

class AdminCourierVerificationUpdate(BaseModel):
    verification_status: VerificationStatus

    @validator('verification_status')
    def status_must_be_valid(cls, v):
        allowed_statuses = [VerificationStatus.APPROVED, VerificationStatus.REJECTED]
        if v not in allowed_statuses:
            raise ValueError(f'Статус должен быть одним из: {allowed_statuses}')
        return v

class CourierForAdmin(UserPublic):
    courier_profile: Optional[CourierProfilePublic] = None
class AdminPayoutUpdate(BaseModel):
    status: PayoutStatus

    @validator('status')
    def status_must_be_valid(cls, v):
        if v not in [PayoutStatus.APPROVED, PayoutStatus.REJECTED]:
            raise ValueError(f'Статус должен быть одним из: {PayoutStatus.APPROVED.value}, {PayoutStatus.REJECTED.value}')
        return v

class CourierForPayout(BaseModel):
    id: int
    first_name: str
    phone: str
    class Config:
        from_attributes = True

class PayoutRequestForAdmin(PayoutRequestPublic):
    courier: CourierForPayout
# ==================================
#         Схемы для Дашборда и Статистики
# ==================================
class GeneralStats(BaseModel):
    total_revenue: Decimal = Field(..., description="Общая выручка за период")
    total_orders: int = Field(..., description="Всего заказов за период")
    new_users: int = Field(..., description="Новых пользователей за период")

class TopRestaurant(BaseModel):
    id: int
    name: str
    order_count: int
    total_revenue: Decimal
    class Config:
        from_attributes = True

class TopCourier(BaseModel):
    id: int
    first_name: str
    deliveries_count: int
    total_earnings: Decimal
    class Config:
        from_attributes = True

class TopClient(BaseModel):
    id: int
    first_name: str
    phone: str
    orders_count: int
    total_spent: Decimal
    class Config:
        from_attributes = True

class DashboardData(BaseModel):
    general_stats: GeneralStats
    top_restaurants: List[TopRestaurant]
    top_couriers: List[TopCourier]
    top_clients: List[TopClient]
# ==================================
#         Схемы для Токена (обновлено)
# ==================================
class Token(BaseModel):
    access_token: str
    refresh_token: str # <-- ДОБАВЛЕНО
    token_type: str = "bearer"