from datetime import date
from pydantic import BaseModel


class LiabilityCreate(BaseModel):
    name: str
    type: str
    amount: float
    date: date


class LiabilityResponse(LiabilityCreate):
    id: int

    class Config:
        from_attributes = True