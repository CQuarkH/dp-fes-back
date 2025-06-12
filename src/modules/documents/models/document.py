from sqlalchemy import Column, Integer, String, DateTime, Enum
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DocumentStatus(PyEnum):
    IN_REVIEW = "IN_REVIEW"
    SIGNED = "SIGNED"
    REJECTED = "REJECTED"

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(Enum(DocumentStatus), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    rejection_date = Column(DateTime, nullable=True)
