from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from .... import crud, models, schemas, deps, database, utils

router = APIRouter()

# =================================================================
#                   Управление Пользователями
# =================================================================

@router.post("/users", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user_by_admin(
    user_in: schemas.AdminUserCreate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """
    Создать нового пользователя (ресторан или администратора).
    """
    db_user = crud.get_user_by_phone(db, phone=user_in.phone)
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким телефоном уже существует.")
    return crud.create_user(db=db, user=user_in)

@router.get("/users", response_model=List[schemas.UserPublic])
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получить список всех пользователей системы."""
    users = crud.get_all_users(db, skip=skip, limit=limit)
    return users

@router.patch("/users/{user_id}/status", response_model=schemas.UserPublic)
def update_user_active_status(
    user_id: int,
    status_in: schemas.UserStatusUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Заблокировать или разблокировать пользователя."""
    db_user = crud.get_user_by_id(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    if db_user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы не можете заблокировать свой собственный аккаунт.")
    return crud.update_user_status(db, db_user=db_user, is_active=status_in.is_active)

# =================================================================
#                   Управление Ресторанами
# =================================================================

@router.get("/restaurants", response_model=List[schemas.RestaurantPublic])
def list_restaurants(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получение списка всех ресторанов."""
    return crud.get_all_restaurants(db)

@router.patch("/restaurants/{restaurant_id}/approve", response_model=schemas.RestaurantPublic)
def approve_restaurant(
    restaurant_id: int,
    approval: schemas.RestaurantApprovalUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Одобрить или отклонить регистрацию ресторана."""
    db_restaurant = crud.get_restaurant_by_id(db, restaurant_id=restaurant_id)
    if not db_restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ресторан не найден.")
    return crud.update_restaurant_approval(db, db_restaurant, is_approved=approval.is_approved)

# =================================================================
#                   Управление Курьерами
# =================================================================
@router.get("/couriers/verification", response_model=List[schemas.CourierForAdmin])
def get_couriers_awaiting_verification(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получить список курьеров, ожидающих верификации."""
    return crud.get_couriers_for_verification(db)

@router.patch("/couriers/{courier_id}/verification", response_model=schemas.CourierProfilePublic)
def verify_courier(
    courier_id: int,
    verification_in: schemas.AdminCourierVerificationUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Одобрить или отклонить профиль курьера."""
    profile = db.query(models.CourierProfile).filter(models.CourierProfile.user_id == courier_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль курьера не найден.")
    return crud.update_courier_verification_status(db, profile=profile, status=verification_in.verification_status)

# =================================================================
#                   Управление Общими Настройками
# =================================================================

@router.get("/settings", response_model=schemas.SystemSettingsPublic)
def get_system_settings(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получение текущих общих настроек (тарифы, зона доставки)."""
    return crud.get_system_settings(db)

@router.put("/settings", response_model=schemas.SystemSettingsPublic)
def update_system_settings(
    settings_in: schemas.SystemSettingsUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Обновление общих настроек (тарифы, зона доставки)."""
    return crud.update_system_settings(db, settings_in)

# =================================================================
#                   Управление Баннерами (ИСПРАВЛЕНО)
# =================================================================

@router.post("/banners", response_model=schemas.BannerPublic, status_code=status.HTTP_201_CREATED)
def create_new_banner(
    title: str = Form(...),
    restaurant_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None), # <-- ИЗМЕНЕНИЕ: Сделали изображение необязательным
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """
    Создать новый рекламный баннер.
    """
    image_url = None
    if image:
        image_url = utils.save_upload_file(image)
        
    banner_in = schemas.BannerCreate(title=title, restaurant_id=restaurant_id)
    return crud.create_banner(db, banner=banner_in, image_url=image_url)


@router.delete("/banners/{banner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_banner_by_id(
    banner_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """
    Удалить баннер по ID.
    """
    db_banner = crud.get_banner_by_id(db, banner_id=banner_id)
    if not db_banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Баннер с таким ID не найден."
        )
    
    crud.delete_banner(db, db_banner=db_banner)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
@router.put("/banners/{banner_id}", response_model=schemas.BannerPublic)
def update_existing_banner(
    banner_id: int,
    title: str = Form(...),
    restaurant_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Обновить существующий баннер."""
    db_banner = crud.get_banner_by_id(db, banner_id=banner_id)
    if not db_banner:
        raise HTTPException(status_code=404, detail="Баннер не найден.")
    
    image_url = utils.save_upload_file(image) if image else None
    banner_in = schemas.BannerUpdate(title=title, restaurant_id=restaurant_id)
    
    return crud.update_banner(db, db_banner=db_banner, banner_in=banner_in, image_url=image_url)
# =================================================================
#                   Управление Глобальными Категориями (ИСПРАВЛЕНО)
# =================================================================
@router.get("/categories", response_model=List[schemas.CategoryPublic])
def get_global_categories(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получить список всех глобальных категорий."""
    return crud.get_categories(db)
@router.post("/categories", response_model=schemas.CategoryPublic, status_code=status.HTTP_201_CREATED)
def create_global_category(
    name: str = Form(...),
    image: Optional[UploadFile] = File(None), # <-- ИЗМЕНЕНИЕ: Сделали изображение необязательным
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Создать новую глобальную категорию для еды."""
    image_url = None
    if image:
        image_url = utils.save_upload_file(image)
        
    category_in = schemas.CategoryCreate(name=name)
    return crud.create_category(db, category=category_in, image_url=image_url)

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_global_category(
    category_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Удалить глобальную категорию."""
    db_category = crud.get_category_by_id(db, category_id=category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Категория не найдена.")
    crud.delete_category(db, db_category=db_category)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# =================================================================
#                   Управление Промокодами
# =================================================================

@router.post("/promo-codes", response_model=schemas.PromoCodePublic, status_code=status.HTTP_201_CREATED)
def create_new_promo_code(
    promo_code_in: schemas.PromoCodeCreate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Создать новый промокод."""
    existing_code = db.query(models.PromoCode).filter(models.PromoCode.code == promo_code_in.code).first()
    if existing_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Промокод с таким названием уже существует.")
    return crud.create_promo_code(db, promo_code=promo_code_in)

@router.get("/promo-codes", response_model=List[schemas.PromoCodePublic])
def get_all_promo_codes(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получить список всех промокодов."""
    return crud.get_all_promo_codes(db)

@router.put("/promo-codes/{promo_code_id}", response_model=schemas.PromoCodePublic)
def update_existing_promo_code(
    promo_code_id: int,
    promo_code_in: schemas.PromoCodeUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Обновить существующий промокод."""
    db_promo_code = crud.get_promo_code_by_id(db, promo_code_id=promo_code_id)
    if not db_promo_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Промокод не найден.")
    if promo_code_in.code != db_promo_code.code:
        existing_code = db.query(models.PromoCode).filter(models.PromoCode.code == promo_code_in.code).first()
        if existing_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Промокод с таким названием уже существует.")
    return crud.update_promo_code(db, db_promo_code=db_promo_code, promo_code_in=promo_code_in)

@router.delete("/promo-codes/{promo_code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_promo_code(
    promo_code_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Удалить промокод."""
    db_promo_code = crud.get_promo_code_by_id(db, promo_code_id=promo_code_id)
    if not db_promo_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Промокод не найден.")
    crud.delete_promo_code(db, db_promo_code=db_promo_code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# =================================================================
#                   Дашборд и Статистика
# =================================================================

@router.get("/dashboard", response_model=schemas.DashboardData)
def get_dashboard_statistics(
    start_date: date = Query(..., description="Дата начала периода (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Дата окончания периода (YYYY-MM-DD)"),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """
    Получить сводную статистику по работе сервиса за указанный период.
    """
    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Дата начала не может быть позже даты окончания.")
    return crud.get_dashboard_stats(db, start_date=start_date, end_date=end_date)
# =================================================================
#                   Управление Выплатами Курьерам
# =================================================================
@router.get("/payouts/pending", response_model=List[schemas.PayoutRequestForAdmin])
def get_pending_payouts(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Получить список всех ожидающих запросов на выплату."""
    return crud.get_pending_payout_requests(db)

@router.patch("/payouts/{request_id}", response_model=schemas.PayoutRequestPublic)
def process_payout_request(
    request_id: int,
    update_in: schemas.AdminPayoutUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(deps.get_current_active_admin)
):
    """Одобрить или отклонить запрос на выплату."""
    db_request = crud.get_payout_request_by_id(db, request_id=request_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Запрос на выплату не найден.")
    if db_request.status != models.PayoutStatus.PENDING:
        raise HTTPException(status_code=400, detail="Этот запрос уже был обработан.")
        
    # В реальном приложении при одобрении здесь был бы вызов API банка для перевода
    if update_in.status == models.PayoutStatus.APPROVED:
        print(f"ИНИЦИИРОВАНА ВЫПЛАТА {db_request.amount} НА КАРТУ {db_request.card_number}")
        
    return crud.update_payout_request_status(db, db_request=db_request, status=update_in.status)
