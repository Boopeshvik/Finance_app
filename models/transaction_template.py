from sqlalchemy import Column, Integer, Float, String, ForeignKey
from database import Base


class TransactionTemplate(Base):
    __tablename__ = "transaction_templates"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String, nullable=False)
    type        = Column(String, nullable=False)
    category    = Column(String, nullable=False)
    amount      = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    sort_order  = Column(Integer, default=0)