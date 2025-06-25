from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from database import Base

class DocumentStatus(PyEnum):
    IN_REVIEW = "IN_REVIEW"
    SIGNED = "SIGNED"
    REJECTED = "REJECTED"

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.IN_REVIEW)
    upload_date = Column(DateTime, default=datetime.utcnow)
    rejection_date = Column(DateTime, nullable=True)
    signed_date = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="documents")

    # Relación con firmas
    signatures = relationship("Signature",back_populates = "document",order_by = "Signature.order",cascade = "all, delete-orphan")
