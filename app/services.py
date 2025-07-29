import httpx
from decimal import Decimal
from datetime import datetime, time, timedelta, timezone
from sqlalchemy.orm import Session
from geopy.distance import geodesic

from .database import SessionLocal
from . import models, schemas, crud, database
from .config import settings


class PayLinkService:
    """
    Сервис для взаимодействия с API PayLink, включая создание сплит-платежей.
    """
    def __init__(self):
        self.api_key = settings.PAYLINK_API_KEY
        self.api_url = settings.PAYLINK_API_URL
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def create_split_payment(
        self, 
        order: models.Order, 
        restaurant_account_id: str,
        platform_account_id: str # ID основного аккаунта платформы из .env
    ) -> str | None:
        """
        Создает платеж с разделением (сплитованием) средств.
        """
        # 1. Рассчитываем доли
        commission_percent = Decimal(config.settings.RESTAURANT_COMMISSION_PERCENT)
        platform_commission = order.items_total_price * (commission_percent / 100)
        
        restaurant_share = order.items_total_price - platform_commission
        
        # Доход платформы = сервисный сбор + комиссия ресторана - скидка по промокоду
        platform_share = (order.service_fee + platform_commission) - order.discount

        # 2. Формируем объект split
        split_rules = [
            {
                "accountId": restaurant_account_id,
                "amount": float(restaurant_share.quantize(Decimal('0.01')))
            },
            {
                "accountId": platform_account_id,
                "amount": float(platform_share.quantize(Decimal('0.01')))
            }
        ]
        
        # 3. Если доставка через приложение, добавляем долю курьера (которая идет на счет платформы)
        if order.delivery_type == models.DeliveryType.APP_COURIER and order.delivery_fee > 0:
            # Деньги за доставку также идут на основной счет платформы
            split_rules[1]["amount"] += float(order.delivery_fee.quantize(Decimal('0.01')))
        
        # Проверка, что сумма всех долей равна итоговой сумме заказа
        total_split_amount = sum(rule['amount'] for rule in split_rules)
        if abs(total_split_amount - float(order.total_price)) > 0.01:
            print("!!! ОШИБКА: Сумма долей не сходится с итоговой суммой заказа!")
            # В реальном приложении здесь нужна более серьезная обработка ошибки
            return None

        payload = {
            "amount": float(order.total_price),
            "orderId": str(order.id),
            "description": f"Оплата заказа #{order.code}",
            "split": split_rules
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.api_url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data.get("data", {}).get("paymentUrl")
            except httpx.HTTPStatusError as e:
                print(f"Ошибка при создании сплит-платежа: {e.response.text}")
                return None

def calculate_order_costs(db: Session, order_in: schemas.OrderCreate) -> dict:
    """
    Рассчитывает полную стоимость заказа, включая все сборы, скидки и доставку.

    Args:
        db: Сессия базы данных.
        order_in: Схема с данными для создания заказа.

    Returns:
        Словарь с детализацией всех стоимостей.
    """
    # 1. Рассчитываем базовую стоимость товаров
    items_total_price = Decimal(0)
    for item_data in order_in.items:
        dish = db.query(models.Dish).filter(models.Dish.id == item_data.dish_id).first()
        if not dish or not dish.is_available:
            raise ValueError(f"Блюдо с ID {item_data.dish_id} недоступно.")
        items_total_price += dish.price * item_data.quantity

    # 2. Рассчитываем сервисный сбор
    service_fee = items_total_price * (Decimal(settings.CLIENT_SERVICE_FEE_PERCENT) / 100)
    service_fee = max(Decimal(settings.MIN_CLIENT_SERVICE_FEE), service_fee)
    service_fee = min(Decimal(settings.MAX_CLIENT_SERVICE_FEE), service_fee)

    # 3. Применяем скидку по промокоду, если он есть
    discount = Decimal(0)
    if order_in.promo_code:
        promo = crud.get_valid_promo_code(db, code=order_in.promo_code)
        if promo:
            if promo.promo_type == models.PromoCodeType.PERCENTAGE:
                discount = items_total_price * (promo.value / 100)
            elif promo.promo_type == models.PromoCodeType.FIXED_AMOUNT:
                discount = promo.value
    
    # 4. Рассчитываем стоимость доставки на основе динамических тарифов (день/ночь)
    tariffs = crud.get_system_settings(db)
    current_hour = datetime.now().hour
    
    is_night = False
    # Проверяем, переходит ли ночной тариф через полночь (например, с 22:00 до 06:00)
    if tariffs.night_tariff_start_hour > tariffs.night_tariff_end_hour:
        if current_hour >= tariffs.night_tariff_start_hour or current_hour < tariffs.night_tariff_end_hour:
            is_night = True
    else: # Если ночь в пределах одного дня (например, с 00:00 до 06:00)
        if tariffs.night_tariff_start_hour <= current_hour < tariffs.night_tariff_end_hour:
            is_night = True

    if is_night:
        delivery_fee = Decimal(tariffs.night_base_rate)
        # Здесь можно добавить логику расчета по километрам, если нужно
        # delivery_fee += distance_km * tariffs.night_rate_per_km
    else:
        delivery_fee = Decimal(tariffs.day_base_rate)
        # delivery_fee += distance_km * tariffs.day_rate_per_km

    # 5. Считаем итоговую сумму
    # Скидка применяется только к стоимости товаров
    total_price = (items_total_price - discount) + service_fee + delivery_fee
    if total_price < 0:
        total_price = Decimal(0)

    return {
        "items_total_price": items_total_price.quantize(Decimal('0.01')),
        "service_fee": service_fee.quantize(Decimal('0.01')),
        "delivery_fee": delivery_fee.quantize(Decimal('0.01')),
        "discount": discount.quantize(Decimal('0.01')),
        "total_price": total_price.quantize(Decimal('0.01')),
    }

def is_address_in_delivery_zone(db: Session, address: models.Address) -> bool:
    """
    Проверяет, находится ли адрес доставки в разрешенной зоне.
    """
    if not address.latitude or not address.longitude:
        # Если у адреса нет координат, считаем его невалидным для проверки
        return False
        
    settings = crud.get_system_settings(db)
    
    city_center = (settings.city_center_lat, settings.city_center_lon)
    delivery_address = (address.latitude, address.longitude)
    
    # Рассчитываем расстояние в километрах
    distance = geodesic(city_center, delivery_address).kilometers
    
    print(f"Расстояние до адреса: {distance:.2f} км. Разрешенный радиус: {settings.delivery_radius_km} км.")
    
    return distance <= settings.delivery_radius_km

def trigger_courier_search(order_id: int):
    """
    Эта функция выполняется в фоне.
    Она ждет нужное время и затем меняет статус заказа на 'Готов к выдаче',
    что делает его видимым для курьеров.
    """
    print(f"Фоновая задача для заказа #{order_id} запущена. Ожидаем...")
    
    # ВАЖНО: В продакшене time.sleep() - плохая практика.
    # Здесь должен быть вызов надежного планировщика (Celery, APScheduler).
    # Мы используем его для простоты демонстрации.
    
    db = SessionLocal()
    try:
        order = crud.get_order_by_id(db, order_id)
        if not order or not order.ready_by_timestamp:
            return

        # Рассчитываем, сколько секунд ждать до момента "за 5 минут до готовности"
        search_start_time = order.ready_by_timestamp - timedelta(minutes=5)
        now = datetime.now(timezone.utc)
        
        wait_seconds = (search_start_time - now).total_seconds()
        
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        
        # Время пришло. Меняем статус.
        crud.set_order_status_to_ready(db, order_id=order_id)

    finally:
        db.close()