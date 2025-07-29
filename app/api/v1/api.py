from fastapi import APIRouter
from .endpoints import (
    auth, orders, payments, restaurants, couriers, admin,
    client_restaurants, addresses, reviews, banners # <-- Добавлен banners
)

api_router = APIRouter()

# --- Эндпоинты для всех ---
api_router.include_router(auth.router, prefix="/auth", tags=["Аутентификация"])
api_router.include_router(client_restaurants.router, prefix="/restaurants", tags=["Клиент: Рестораны и Меню"])
api_router.include_router(banners.router, prefix="/banners", tags=["Клиент: Баннеры"]) # <-- НОВЫЙ РОУТЕР

# --- Эндпоинты для аутентифицированных пользователей (клиентов) ---
api_router.include_router(orders.router, prefix="/orders", tags=["Клиент: Заказы"])
api_router.include_router(addresses.router, prefix="/addresses", tags=["Клиент: Адреса"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Клиент: Отзывы"])

# --- Эндпоинты для других ролей ---
api_router.include_router(restaurants.router, prefix="/my-restaurant", tags=["Владелец Ресторана"])
api_router.include_router(couriers.router, prefix="/courier", tags=["Курьер"])
api_router.include_router(admin.router, prefix="/admin", tags=["Администратор"])

# --- Системные эндпоинты ---
api_router.include_router(payments.router, prefix="/payments", tags=["Платежи (системное)"])
