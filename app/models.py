# app/models.py
from pydantic import BaseModel, Field


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