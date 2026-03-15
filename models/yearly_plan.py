from sqlalchemy import Column, Integer, Float, ForeignKey
from database import Base

class YearlyPlan(Base):
    __tablename__ = "yearly_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    planned_income = Column(Float, nullable=False)
    planned_expense = Column(Float, nullable=False)
    planned_savings = Column(Float, nullable=False)
