from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from database import Base


class Investment(Base):
    __tablename__ = "investments"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    name           = Column(String, nullable=False)
    start_date     = Column(Date, nullable=False)
    total_invested = Column(Float, nullable=False, default=0)
    current_value  = Column(Float, nullable=False, default=0)
    notes          = Column(String, nullable=True)


class InvestmentHistory(Base):
    __tablename__ = "investment_history"

    id            = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id"), nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    month         = Column(Integer, nullable=False)
    year          = Column(Integer, nullable=False)
    amount_added  = Column(Float, nullable=False, default=0)
    current_value = Column(Float, nullable=False)
    note          = Column(String, nullable=True)