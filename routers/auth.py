from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth_schema import UserCreate, UserResponse, UserUpdate, PasswordReset
from auth import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/register")
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    role = data.role.strip().lower()

    if role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'user'")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=username,
        hashed_password=hash_password(data.password),
        role=role,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active
    }


@router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip().lower()

    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active
    }


# -----------------------------
# Admin user management
# -----------------------------

@router.get("/admin/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    return db.query(User).order_by(User.id.asc()).all()


@router.post("/admin/users", response_model=UserResponse)
def create_user_by_admin(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    username = data.username.strip().lower()
    role = data.role.strip().lower()

    if role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'user'")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=username,
        hashed_password=hash_password(data.password),
        role=role,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/admin/users/{user_id}", response_model=UserResponse)
def update_user_by_admin(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    username = data.username.strip().lower()
    role = data.role.strip().lower()

    if role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'user'")

    duplicate = (
        db.query(User)
        .filter(User.username == username, User.id != user_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Another user already has this username")

    user.username = username
    user.role = role
    user.is_active = data.is_active

    db.commit()
    db.refresh(user)
    return user


@router.put("/admin/users/{user_id}/reset-password")
def reset_user_password_by_admin(
    user_id: int,
    data: PasswordReset,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(data.new_password)

    db.commit()

    return {"message": f"Password reset successful for user '{user.username}'"}


@router.delete("/admin/users/{user_id}")
def delete_user_by_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Admin cannot delete their own account")

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}