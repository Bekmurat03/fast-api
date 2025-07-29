from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from . import crud, models, security
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_phone(db, phone=phone)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Неактивный пользователь.")
    return current_user

def get_current_active_restaurant_owner(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    if current_user.role != models.UserRole.RESTAURANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ разрешен только для ресторанов.")
    return current_user

def get_current_active_courier(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    if current_user.role != models.UserRole.COURIER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ разрешен только для курьеров.")
    return current_user

def get_current_active_admin(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ разрешен только для администраторов.")
    return current_user