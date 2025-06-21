from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from database import Base

class UserRole(PyEnum):
    EMPLOYEE = "EMPLOYEE"
    SUPERVISOR = "SUPERVISOR"
    SIGNER = "SIGNER"
    INSTITUTIONAL_MANAGER = "INSTITUTIONAL_MANAGER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    # Relationship with documents
    documents = relationship("Document", back_populates="user")
