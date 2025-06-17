# modules/notifications/controllers/notification_controller.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import SessionLocal
from modules.notifications.repositories.notification_repository import NotificationRepository
from modules.notifications.services.notification_service import NotificationService
from modules.notifications.models.schemas import (
    NotificationResponse,
    ChangeDocumentStateRequest,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    repo = NotificationRepository(db)
    return NotificationService(repo)


@router.get(
    "/users/{user_id}",
    response_model=List[NotificationResponse],
    summary="Obtener notificaciones de un usuario"
)
def list_notifications(
    user_id: int,
    service: NotificationService = Depends(get_notification_service)
):
    return service.get_notifications(user_id)


@router.post(
    "/users/{user_id}/document-state-change",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear notificación de cambio de estado de documento"
)
def create_change_state_notification(
    user_id: int,
    payload: ChangeDocumentStateRequest,
    service: NotificationService = Depends(get_notification_service)
):
    return service.create_change_document_state_notification(
        user_id=user_id,
        document_name=payload.document_name,
        new_state=payload.new_state
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Marcar notificación como leída"
)
def mark_notification_as_read(
    notification_id: int,
    service: NotificationService = Depends(get_notification_service)
):
    notif = service.mark_as_read(notification_id)
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )
    return notif
