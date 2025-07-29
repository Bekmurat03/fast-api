from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from .... import crud, schemas, security, database, models
from ....config import settings

router = APIRouter()

# Схема для получения refresh токена из заголовка
oauth2_scheme_refresh = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/refresh-token")

@router.post("/register", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
def public_user_registration(
    user_in: schemas.UserPublicRegister,
    db: Session = Depends(database.get_db)
):
    """
    Публичная регистрация для новых клиентов и курьеров.
    """
    db_user = crud.get_user_by_phone(db, phone=user_in.phone)
    if db_user:
        raise HTTPException(status_code=400, detail="Телефон уже зарегистрирован.")
    
    return crud.create_user(db=db, user=user_in)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Принимает телефон и пароль, возвращает access и refresh токены.
    """
    user = crud.get_user_by_phone(db, phone=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильный номер телефона или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(data={"sub": user.phone})
    refresh_token = security.create_refresh_token(data={"sub": user.phone})
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh-token", response_model=schemas.Token)
def refresh_access_token(
    refresh_token: str = Depends(oauth2_scheme_refresh),
    db: Session = Depends(database.get_db)
):
    """
    Принимает refresh_token и возвращает новую пару токенов.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить refresh-токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_phone(db, phone=phone)
    if user is None:
        raise credentials_exception
        
    new_access_token = security.create_access_token(data={"sub": user.phone})
    new_refresh_token = security.create_refresh_token(data={"sub": user.phone})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
