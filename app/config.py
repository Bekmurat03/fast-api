from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str

    # Настройки JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # --- НОВЫЕ ПОЛЯ ---
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # PayLink API
    PAYLINK_API_KEY: str
    PAYLINK_API_URL: str
    PLATFORM_PAYLINK_ACCOUNT_ID: str

    # Бизнес-логика
    RESTAURANT_COMMISSION_PERCENT: float
    CLIENT_SERVICE_FEE_PERCENT: float
    MIN_CLIENT_SERVICE_FEE: float
    MAX_CLIENT_SERVICE_FEE: float
    DELIVERY_BASE_RATE: float
    DELIVERY_RATE_PER_KM: float

    class Config:
        env_file = ".env"

settings = Settings()
