from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
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
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with documents
    documents = relationship("Document", back_populates="user")

    # Relationship with notifications
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )
