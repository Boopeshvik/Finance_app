from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: str
    role: str
    is_active: bool


class PasswordReset(BaseModel):
    new_password: str