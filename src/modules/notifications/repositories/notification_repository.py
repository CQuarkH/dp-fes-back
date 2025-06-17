from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from modules.notifications.models.notification import Notification

class NotificationRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def save(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def find_by_user_id(self, user_id: int) -> List[Notification]:
        return (
            self.db
            .query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    def update(self, notification_id: int, data: Dict) -> Optional[Notification]:
        notif = self.db.get(Notification, notification_id)
        if not notif:
            return None
        for field, value in data.items():
            setattr(notif, field, value)
        self.db.commit()
        self.db.refresh(notif)
        return notif
