from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # income or expense
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)