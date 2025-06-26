from modules.documents.models.user import UserRole

ROLE_PERMISSIONS = {
    UserRole.EMPLOYEE: ["upload"],
    UserRole.SUPERVISOR: ["review", "sign", "reject"],
    UserRole.SIGNER: ["sign"],
    UserRole.INSTITUTIONAL_MANAGER: ["review", "sign", "reject", "manage"],
    UserRole.ADMIN: ["upload", "review", "sign", "reject", "manage"],
}

def can_perform_action(user_role: UserRole, action: str) -> bool:
    return action in ROLE_PERMISSIONS.get(user_role, [])
