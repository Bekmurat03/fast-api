from fastapi import APIRouter, Request, Response, status, Depends
from sqlalchemy.orm import Session
from .... import crud, database

router = APIRouter()

@router.post("/webhook/paylink", status_code=status.HTTP_200_OK, include_in_schema=False)
async def paylink_webhook(request: Request, db: Session = Depends(database.get_db)):
    """
    Обработка веб-хуков от PayLink.
    ВАЖНО: В реальном проекте здесь нужна проверка IP-адреса или подписи запроса.
    """
    data = await request.json()
    
    event_type = data.get("type")
    if event_type == "payment.success":
        order_id_str = data.get("data", {}).get("orderId")
        if order_id_str and order_id_str.isdigit():
            crud.mark_order_as_paid(db=db, order_id=int(order_id_str))
            
    return Response(status_code=status.HTTP_200_OK)
