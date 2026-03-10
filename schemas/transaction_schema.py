from datetime import date
from typing import Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    type: str
    category: str
    amount: float
    date: date
    description: Optional[str] = None


class TransactionResponse(TransactionCreate):
    id: int

    class Config:
        from_attributes = True