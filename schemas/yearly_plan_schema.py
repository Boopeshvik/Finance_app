from pydantic import BaseModel


class YearlyPlanCreate(BaseModel):
    year: int
    planned_income: float
    planned_expense: float
    planned_savings: float


class YearlyPlanResponse(YearlyPlanCreate):
    id: int

    class Config:
        from_attributes = True