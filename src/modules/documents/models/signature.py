# src/modules/documents/models/signature.py

from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"),     nullable=False)
    ts          = Column(DateTime, default=datetime.utcnow, nullable=False)
    order       = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False)

    document = relationship("Document", back_populates="signatures")
    user     = relationship("User")
