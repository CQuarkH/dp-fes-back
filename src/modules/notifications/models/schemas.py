from pydantic import BaseModel
from datetime import datetime

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    read: bool = False

    model_config = {"from_attributes": True}

class ChangeDocumentStateRequest(BaseModel):
    document_name: str
    new_state: str
