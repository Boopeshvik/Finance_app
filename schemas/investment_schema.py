from pydantic import BaseModel
from typing import Optional


class InvestmentCreate(BaseModel):
    name:            str
    month:           int
    year:            int
    amount_invested: float
    current_value:   float
    notes:           Optional[str] = None


class InvestmentUpdate(BaseModel):
    name:            str
    month:           int
    year:            int
    amount_invested: float
    current_value:   float
    notes:           Optional[str] = None


class InvestmentResponse(BaseModel):
    id:              int
    user_id:         int
    name:            str
    month:           int
    year:            int
    amount_invested: float
    current_value:   float
    notes:           Optional[str]

    class Config:
        from_attributes = True