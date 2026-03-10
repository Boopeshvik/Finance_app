from datetime import date
from pydantic import BaseModel


class GoalCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float
    target_date: date


class GoalUpdate(BaseModel):
    name: str
    target_amount: float
    current_amount: float
    target_date: date


class GoalResponse(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    target_date: date
    progress_percentage: float
    remaining_amount: float

    class Config:
        from_attributes = True