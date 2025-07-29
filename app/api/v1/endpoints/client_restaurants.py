from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .... import crud, schemas, database

router = APIRouter()

@router.get("/", response_model=List[schemas.RestaurantForList])
def list_restaurants(
    db: Session = Depends(database.get_db), skip: int = 0, limit: int = 20
):
    """Список активных и одобренных ресторанов для клиентов."""
    return crud.get_active_restaurants(db, skip=skip, limit=limit)

@router.get("/{restaurant_id}", response_model=schemas.RestaurantPublicDetail)
def restaurant_details(restaurant_id: int, db: Session = Depends(database.get_db)):
    """Детальная информация о ресторане с полным меню."""
    db_restaurant = crud.get_restaurant_details(db, restaurant_id=restaurant_id)
    if db_restaurant is None:
        raise HTTPException(status_code=404, detail="Ресторан не найден.")
    return db_restaurant
