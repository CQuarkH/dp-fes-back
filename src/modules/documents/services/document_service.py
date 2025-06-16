from sqlalchemy.orm import Session
from modules.documents.models.document import Document, DocumentStatus
from modules.documents.models.user import User
from modules.documents.services.document_state_service import DocumentStateService
from datetime import datetime

class DocumentService:

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
