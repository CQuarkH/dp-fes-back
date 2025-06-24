from datetime import datetime
from sqlalchemy.orm import Session
from modules.documents.models.document import Document, DocumentStatus
from modules.documents.models.user import User, UserRole
from typing import Optional
from modules.notifications.repositories.notification_repository import NotificationRepository
from modules.notifications.services.notification_service import NotificationService

class DocumentStateError(Exception):
    """Exception for document state transition errors"""
    pass

class DocumentStateService:

    @staticmethod
    def can_change_state(user: User, document: Document, new_state: DocumentStatus) -> bool:
        """
        Defines transition rules based on user role
        """
        current_state = document.state
        user_role = user.role

        if user_role == UserRole.EMPLOYEE:
            return False

        elif user_role == UserRole.SUPERVISOR:
            if current_state == DocumentStatus.UNDER_REVIEW:
                return new_state in [DocumentStatus.SIGNED, DocumentStatus.REJECTED]
            return False

        elif user_role == UserRole.ADMINISTRATOR:
            return True

        return False

    @staticmethod
    def change_document_state(session: Session, document_id: int, user_id: int,
                             new_state: DocumentStatus) -> Document:
        """
        Changes document state after validating permissions and updates dates
        """
        document = session.get(Document, document_id)
        user = session.get(User, user_id)

        if not document:
            raise DocumentStateError("Document not found")

        if not user:
            raise DocumentStateError("User not found")

        if not DocumentStateService.can_change_state(user, document, new_state):
            raise DocumentStateError(
                f"User with role {user.role.value} cannot change document "
                f"from {document.state.value} to {new_state.value}"
            )

        previous_state = document.state
        document.state = new_state

        if new_state == DocumentStatus.REJECTED:
            document.rejection_date = datetime.utcnow()
        elif new_state == DocumentStatus.SIGNED:
            document.signing_date = datetime.utcnow()

        session.commit()

        notif_repo = NotificationRepository(session)
        notif_service = NotificationService(notif_repo)
        notif_service.create_change_document_state_notification(
            user_id=document.user_id,
            document_name=document.name,
            new_state=new_state.value
        )

        print(f"Document {document.id} changed from {previous_state.value} to {new_state.value}")
        return document

    @staticmethod
    def get_allowed_transitions(user: User, document: Document) -> list[DocumentStatus]:
        """
        Returns list of states the document can transition to
        """
        transitions = []

        for state in DocumentStatus:
            if DocumentStateService.can_change_state(user, document, state):
                transitions.append(state)

        return transitions
