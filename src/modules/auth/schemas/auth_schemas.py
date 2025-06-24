from pydantic import BaseModel, EmailStr
from typing import Optional
from modules.documents.models.user import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_name: str
    user_role: str

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True
