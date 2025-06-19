import hashlib

from sqlalchemy.orm import Session
from modules.documents.models.document import Document, DocumentStatus
from modules.documents.models.signature import Signature
from modules.documents.models.user import User
from modules.documents.services.document_state_service import DocumentStateService
from datetime import datetime

class DocumentService:

    @staticmethod
    def add_signature(session: Session, document_id: int, user_id: int) -> Signature:
        """Añade una firma simple con límite de 5 por documento y calcula hash."""
        # 1) Cargar entidad
        doc = session.get(Document, document_id)
        user = session.get(User, user_id)
        if not doc or not user:
            raise ValueError("Documento o usuario no existe")

        # 2) Límite de 5 firmas
        existing = doc.signatures
        if len(existing) >= 5:
            raise ValueError("Máximo de 5 firmas alcanzado")

        # 3) Leer archivo y calcular SHA‑256
        with open(doc.file_path, "rb") as f:
            data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()

        # 4) Determinar orden (1..n)
        next_order = (max([s.order for s in existing]) + 1) if existing else 1

        # 5) Crear firma
        sig = Signature(
            document_id=document_id,
            user_id=user_id,
            ts=datetime.utcnow(),
            order=next_order,
            sha256_hash=sha256
        )
        session.add(sig)
        session.commit()
        return sig

    @staticmethod
    def upload_document(session: Session, user_id: int, name: str, file_path: str) -> Document:
        """
        Upload a new document (always starts as IN_REVIEW)
        """
        document = Document(
            name=name,
            file_path=file_path,
            status=DocumentStatus.IN_REVIEW,
            user_id=user_id,
            upload_date=datetime.utcnow()
        )

        session.add(document)
        session.commit()
        return document

    @staticmethod
    def sign_document(session: Session, document_id: int, user_id: int) -> Document:
        """
        Sign a document (change to SIGNED)
        """
        return DocumentStateService.change_document_status(
            session, document_id, user_id, DocumentStatus.SIGNED
        )

    @staticmethod
    def reject_document(session: Session, document_id: int, user_id: int) -> Document:
        """
        Reject a document (change to REJECTED)
        """
        return DocumentStateService.change_document_status(
            session, document_id, user_id, DocumentStatus.REJECTED
        )
