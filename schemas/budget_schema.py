from pydantic import BaseModel


class BudgetCreate(BaseModel):
    category: str
    month: int
    year: int
    amount: float


class BudgetUpdate(BaseModel):
    category: str
    month: int
    year: int
    amount: float


class BudgetResponse(BudgetCreate):
    id: int

    class Config:
        from_attributes = True