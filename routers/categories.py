from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.category import Category
from models.user import User
from routers.auth import get_current_user
from schemas.category_schema import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryResponse)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category_type = data.type.strip().lower()
    category_name = data.name.strip().lower()

    if category_type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="type must be either 'income' or 'expense'")

    existing = (
        db.query(Category)
        .filter(Category.name == category_name, Category.user_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    category = Category(
        name=category_name,
        type=category_type,
        user_id=current_user.id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/", response_model=list[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Category)
        .filter(Category.user_id == current_user.id)
        .order_by(Category.type.asc(), Category.name.asc())
        .all()
    )


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == current_user.id)
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    category_type = data.type.strip().lower()
    category_name = data.name.strip().lower()

    if category_type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="type must be either 'income' or 'expense'")

    duplicate = (
        db.query(Category)
        .filter(
            Category.name == category_name,
            Category.user_id == current_user.id,
            Category.id != category_id
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Another category with this name already exists")

    category.name = category_name
    category.type = category_type

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == current_user.id)
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}