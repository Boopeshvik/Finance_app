from pydantic import BaseModel


class MonthlyPlanCreate(BaseModel):
    month: int
    year: int
    planned_income: float
    planned_expense: float
    planned_savings: float


class MonthlyPlanResponse(MonthlyPlanCreate):
    id: int

    class Config:
        from_attributes = True