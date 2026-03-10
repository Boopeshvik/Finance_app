from sqlalchemy import Column, Integer, Float
from database import Base


class MonthlyPlan(Base):
    __tablename__ = "monthly_plans"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    planned_income = Column(Float, nullable=False)
    planned_expense = Column(Float, nullable=False)
    planned_savings = Column(Float, nullable=False)