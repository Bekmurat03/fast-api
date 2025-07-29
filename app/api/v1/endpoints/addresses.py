from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .... import crud, models, schemas, deps, database

router = APIRouter()

@router.post("/", response_model=schemas.AddressPublic, status_code=status.HTTP_201_CREATED)
def create_address(
    address_in: schemas.AddressCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Добавить новый адрес."""
    return crud.create_user_address(db, address=address_in, user_id=current_user.id)

@router.get("/", response_model=List[schemas.AddressPublic])
def get_my_addresses(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Получить список своих адресов."""
    return crud.get_user_addresses(db, user_id=current_user.id)

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Удалить адрес."""
    db_address = crud.get_address_by_id(db, address_id=address_id)
    if not db_address or db_address.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Адрес не найден.")
    crud.delete_address(db, db_address=db_address)
    return {"ok": True}
