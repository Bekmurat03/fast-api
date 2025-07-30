from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .... import schemas, crud, models, deps

router = APIRouter()

@router.get("/me", response_model=schemas.UserPublic)
def get_current_user(
    current_user: models.User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Получение данных текущего авторизованного пользователя
    """
    return current_user