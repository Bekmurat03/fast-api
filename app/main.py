from fastapi import FastAPI
from .database import Base, engine
from .api.v1.api import api_router

# Создает все таблицы в БД при первом запуске.
# В продакшене лучше использовать системы миграций, такие как Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JetFood API",
    description="Бэкенд для сервиса доставки еды JetFood.",
    version="1.0.0",
)

# Подключаем все роутеры версии v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def read_root():
    """Корневой эндпоинт для проверки работоспособности API."""
    return {"message": "Welcome to JetFood API v1"}
