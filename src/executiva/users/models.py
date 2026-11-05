from sqlalchemy import Column, Integer, String

from executiva.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, index=True, nullable=False)
    password = Column(String, nullable=False)