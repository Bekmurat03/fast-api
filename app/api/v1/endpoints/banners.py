from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .... import crud, schemas, database

router = APIRouter()

@router.get("/", response_model=List[schemas.BannerPublic])
def get_active_banners(db: Session = Depends(database.get_db)):
    """
    Получить список активных баннеров для главной страницы приложения.
    """
    return crud.get_active_banners(db)
