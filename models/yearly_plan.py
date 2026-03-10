from sqlalchemy import Column, Integer, Float
from database import Base


class YearlyPlan(Base):
    __tablename__ = "yearly_plans"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, unique=True)
    planned_income = Column(Float, nullable=False)
    planned_expense = Column(Float, nullable=False)
    planned_savings = Column(Float, nullable=False)