import enum
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, DateTime,
    Enum, Numeric, Text, Float, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# --- Enum типы (без изменений) ---
class UserRole(str, enum.Enum):
    CLIENT = "client"
    COURIER = "courier"
    RESTAURANT = "restaurant"
    ADMIN = "admin"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    ACCEPTED = "accepted"
    AWAITING_COURIER_SEARCH = "awaiting_courier_search"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    ON_THE_WAY = "on_the_way"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    
class DeliveryType(str, enum.Enum):
    APP_COURIER = "app_courier"
    SELF_DELIVERY = "self_delivery"

class VerificationStatus(str, enum.Enum):
    NOT_SUBMITTED = "not_submitted"
    ON_REVIEW = "on_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    
class PromoCodeType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"

class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
# --- Модели ---
class User(Base):
    # ... (без изменений) ...
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, index=True)
    role = Column(Enum(UserRole), default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    date_joined = Column(DateTime(timezone=True), server_default=func.now())
    
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", foreign_keys="[Order.user_id]")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    
    courier_profile = relationship("CourierProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    owned_restaurant = relationship("Restaurant", back_populates="owner", uselist=False, cascade="all, delete-orphan")

class Address(Base):
    # ... (без изменений) ...
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    city = Column(String, default="Zhanaozen")
    street = Column(String, nullable=False)
    house_number = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    user = relationship("User", back_populates="addresses")

class Restaurant(Base):
    __tablename__ = "restaurants"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo = Column(String, nullable=True)
    banner = Column(String, nullable=True)
    address = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    average_rating = Column(Numeric(3, 2), default=0.00)
    review_count = Column(Integer, default=0)
    
    # --- ИЗМЕНЕНИЯ ---
    # Убираем balance, добавляем paylink_account_id
    paylink_account_id = Column(String, nullable=True, unique=True)
    
    owner = relationship("User", back_populates="owned_restaurant")
    dishes = relationship("Dish", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="restaurant")
    reviews = relationship("Review", back_populates="restaurant")

# --- ИЗМЕНЕННАЯ МОДЕЛЬ ---
class Category(Base):
    """Глобальная модель категорий, управляемая админом."""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    image_url = Column(String, nullable=True)
    
    dishes = relationship("Dish", back_populates="category")

# --- ИЗМЕНЕННАЯ МОДЕЛЬ ---
class Dish(Base):
    """Блюдо теперь напрямую связано с рестораном и глобальной категорией."""
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False) # <-- Связь с рестораном
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False) # <-- Связь с глобальной категорией
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2))
    image = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    
    restaurant = relationship("Restaurant", back_populates="dishes")
    category = relationship("Category", back_populates="dishes")
    items = relationship("OrderItem", back_populates="dish")

# ... (остальные модели без изменений) ...
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    courier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    address_text = Column(Text)
    items_total_price = Column(Numeric(10, 2))
    delivery_fee = Column(Numeric(10, 2))
    service_fee = Column(Numeric(10, 2))
    discount = Column(Numeric(10, 2), default=0)
    total_price = Column(Numeric(10, 2))
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    payment_invoice_id = Column(String, nullable=True, index=True)
    delivery_type = Column(Enum(DeliveryType), nullable=True)
    preparation_time_minutes = Column(Integer, nullable=True)
    ready_by_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="orders", foreign_keys=[user_id])
    restaurant = relationship("Restaurant", back_populates="orders")
    courier = relationship("User", foreign_keys=[courier_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="order", uselist=False, cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    dish_id = Column(Integer, ForeignKey("dishes.id"))
    quantity = Column(Integer)
    price_at_time_of_order = Column(Numeric(10, 2))
    
    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="items")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    order = relationship("Order", back_populates="review")
    user = relationship("User", back_populates="reviews")
    restaurant = relationship("Restaurant", back_populates="reviews")

class PromoCode(Base):
    __tablename__ = "promo_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    promo_type = Column(Enum(PromoCodeType), nullable=False)
    value = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)
    valid_from = Column(Date)
    valid_to = Column(Date)
    max_uses = Column(Integer, default=1)
    times_used = Column(Integer, default=0)

class Banner(Base):
    __tablename__ = "banners"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    restaurant = relationship("Restaurant")

class CourierProfile(Base):
    __tablename__ = "courier_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.NOT_SUBMITTED)
    is_online = Column(Boolean, default=False)
    id_card_image_url = Column(String, nullable=True)
    card_number = Column(String, nullable=True)
    
    # --- НОВОЕ ПОЛЕ: Кошелек ---
    balance = Column(Numeric(10, 2), default=0.00)
    
    user = relationship("User", back_populates="courier_profile")
    payout_requests = relationship("PayoutRequest", back_populates="courier_profile")
class PayoutRequest(Base):
    __tablename__ = "payout_requests"
    id = Column(Integer, primary_key=True, index=True)
    courier_profile_id = Column(Integer, ForeignKey("courier_profiles.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    card_number = Column(String, nullable=False) # Дублируем номер карты на момент запроса
    status = Column(Enum(PayoutStatus), default=PayoutStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True) # Время обработки админом
    
    courier_profile = relationship("CourierProfile", back_populates="payout_requests")

class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    # Тарифы
    day_base_rate = Column(Numeric(10, 2), default=500.0)
    day_rate_per_km = Column(Numeric(10, 2), default=100.0)
    night_base_rate = Column(Numeric(10, 2), default=800.0)
    night_rate_per_km = Column(Numeric(10, 2), default=150.0)
    night_tariff_start_hour = Column(Integer, default=22)
    night_tariff_end_hour = Column(Integer, default=6)
    
    # --- НОВЫЕ ПОЛЯ: Зона Доставки ---
    # Координаты центра города (например, центр Жагаозена)
    city_center_lat = Column(Float, default=43.3333) 
    city_center_lon = Column(Float, default=52.8667)
    # Радиус доставки в километрах
    delivery_radius_km = Column(Float, default=10.0)
