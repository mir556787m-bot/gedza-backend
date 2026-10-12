# app/models.py
from pydantic import BaseModel, Field
from typing import Optional, List


class MenuItem(BaseModel):
    id: str
    name: str
    price: float
    old_price: Optional[float] = None
    weight: Optional[str] = None
    category: Optional[str] = None
    badge: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None


class MenuResponse(BaseModel):
    items: List[MenuItem]
    updated_at: str


class CartUpdate(BaseModel):
    user_id: int
    item_id: str
    quantity: int = Field(..., description="+1 добавить, -1 убрать")


class OrderCreate(BaseModel):
    user_id: int
    address: str
    phone: str
    comment: str = ""
    payment_method: str = "sbp"
    # 👇 Согласие на маркетинг — отдельно от оформления
    marketing_consent: bool = True