from sqlalchemy import Column, Integer, Float, String, ForeignKey
from database import Base


class Investment(Base):
    __tablename__ = "investments"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    name            = Column(String, nullable=False)       # e.g. "Vanguard", "Trading 212"
    month           = Column(Integer, nullable=False)       # 1-12
    year            = Column(Integer, nullable=False)
    amount_invested = Column(Float, nullable=False)         # how much you put in this period
    current_value   = Column(Float, nullable=False)         # what it's worth now
    notes           = Column(String, nullable=True)