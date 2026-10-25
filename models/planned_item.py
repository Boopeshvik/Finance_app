from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from database import Base


class PlannedItem(Base):
    __tablename__ = "planned_items"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date        = Column(Date, nullable=False, index=True)
    type        = Column(String, nullable=False)          # income / expense / investment
    category    = Column(String, nullable=False)
    amount      = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    status      = Column(String, nullable=False, default="planned")   # planned / done