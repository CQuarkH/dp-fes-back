# modules/notifications/services/notification_service.py
from typing import List, Optional

from modules.notifications.models.notification import Notification
from modules.notifications.repositories.notification_repository import NotificationRepository

class NotificationTemplate:
    def __init__(self, user_id: int, title: str, message: str):
        self.user_id = user_id
        self.title = title
        self.message = message

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message
        }

class ChangeDocumentStateNotification(NotificationTemplate):
    def __init__(self, user_id: int, document_name: str, new_state: str):
        readable_statuses = {
            'IN_REVIEW': 'En revisión',
            'SIGNED': 'Firmado',
            'REJECTED': 'Rechazado'
        }
        title = "Cambio de estado de documento"
        status_human = readable_statuses.get(new_state, new_state)
        message = f"El documento '{document_name}' ha cambiado de estado a: '{status_human}'."
        super().__init__(user_id, title, message)

class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.notification_repository = repository

    def create_change_document_state_notification(
        self,
        user_id: int,
        document_name: str,
        new_state: str
    ) -> Notification:
        template = ChangeDocumentStateNotification(user_id, document_name, new_state)
        notif = Notification(
            user_id=template.user_id,
            title=template.title,
            message=template.message
        )
        return self.notification_repository.save(notif)

    def get_notifications(self, user_id: int) -> List[Notification]:
        return self.notification_repository.find_by_user_id(user_id)

    def mark_as_read(self, notification_id: int) -> Optional[Notification]:
        return self.notification_repository.update(notification_id, {'read': True})
