from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings  # <--- ИЗМЕНЕНИЕ: импортируем из config.py

# Удаляем старый класс Settings отсюда

engine = create_engine(settings.DATABASE_URL) # <--- ИЗМЕНЕНИЕ: используем импортированный settings
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Зависимость для получения сессии БД в эндпоинтах
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()