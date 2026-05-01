from pydantic import BaseModel
from typing import Optional
from datetime import date


class InvestmentCreate(BaseModel):
    name:           str
    start_date:     date
    total_invested: float
    current_value:  float
    notes:          Optional[str] = None


class InvestmentUpdate(BaseModel):
    name:           str
    start_date:     date
    total_invested: float
    current_value:  float
    notes:          Optional[str] = None


class InvestmentResponse(BaseModel):
    id:             int
    user_id:        int
    name:           str
    start_date:     date
    total_invested: float
    current_value:  float
    notes:          Optional[str]

    class Config:
        from_attributes = True


class HistoryCreate(BaseModel):
    month:        int
    year:         int
    amount_added: float
    current_value: float
    note:         Optional[str] = None


class HistoryResponse(BaseModel):
    id:            int
    investment_id: int
    month:         int
    year:          int
    amount_added:  float
    current_value: float
    note:          Optional[str]

    class Config:
        from_attributes = True