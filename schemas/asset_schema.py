from datetime import date
from pydantic import BaseModel


class AssetCreate(BaseModel):
    name: str
    type: str
    value: float
    date: date


class AssetResponse(AssetCreate):
    id: int

    class Config:
        from_attributes = True