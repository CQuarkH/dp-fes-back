from fastapi import Depends, HTTPException, status
from modules.documents.models.user import User
from modules.documents.services.permission import can_perform_action
from modules.auth.controllers.auth_controller import get_current_user

def require_permission(action: str):
    def dependency(current_user: User = Depends(get_current_user)):
        if not can_perform_action(current_user.role, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with role '{current_user.role.value}' cannot perform '{action}'"
            )
        return current_user
    return dependency
