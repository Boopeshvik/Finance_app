from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract

from database import get_db
from models.budget import Budget
from models.transaction import Transaction
from models.category import Category
from models.user import User
from routers.auth import get_current_user
from schemas.budget_schema import BudgetCreate, BudgetUpdate, BudgetResponse

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("/", response_model=BudgetResponse)
def create_budget(
    data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category_name = data.category.strip().lower()

    category = (
        db.query(Category)
        .filter(Category.name == category_name, Category.user_id == current_user.id)
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_name}' does not exist. Please create it first."
        )

    if category.type != "expense":
        raise HTTPException(
            status_code=400,
            detail=f"Budget can only be created for expense categories. '{category_name}' is '{category.type}'."
        )

    existing = (
        db.query(Budget)
        .filter(
            Budget.category == category_name,
            Budget.month == data.month,
            Budget.year == data.year,
            Budget.user_id == current_user.id
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Budget already exists for this category, month, and year")

    budget = Budget(
        category=category_name,
        month=data.month,
        year=data.year,
        amount=data.amount,
        user_id=current_user.id
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/", response_model=list[BudgetResponse])
def get_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Budget)
        .filter(Budget.user_id == current_user.id)
        .order_by(Budget.year.desc(), Budget.month.desc(), Budget.category.asc())
        .all()
    )


@router.put("/{budget_id}")
def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    category_name = data.category.strip().lower()

    category = (
        db.query(Category)
        .filter(Category.name == category_name, Category.user_id == current_user.id)
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_name}' does not exist. Please create it first."
        )

    if category.type != "expense":
        raise HTTPException(
            status_code=400,
            detail=f"Budget can only be created for expense categories. '{category_name}' is '{category.type}'."
        )

    duplicate = (
        db.query(Budget)
        .filter(
            Budget.category == category_name,
            Budget.month == data.month,
            Budget.year == data.year,
            Budget.user_id == current_user.id,
            Budget.id != budget_id
        )
        .first()
    )

    if duplicate:
        raise HTTPException(status_code=400, detail="Another budget already exists for this category, month, and year")

    budget.category = category_name
    budget.month = data.month
    budget.year = data.year
    budget.amount = data.amount

    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(budget)
    db.commit()

    return {"message": "Budget deleted successfully"}


@router.get("/monthly/{year}/{month}")
def get_monthly_budget_status(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == current_user.id)
        .filter(Budget.year == year, Budget.month == month)
        .order_by(Budget.category.asc())
        .all()
    )

    results = []
    total_budget = 0
    total_spent = 0

    for budget in budgets:
        spent = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == current_user.id,
                extract("year", Transaction.date) == year,
                extract("month", Transaction.date) == month,
                Transaction.type == "expense",
                Transaction.category == budget.category
            )
            .all()
        )

        actual_spent = sum(t.amount for t in spent)
        remaining = budget.amount - actual_spent
        over_budget = max(0, actual_spent - budget.amount)
        usage_percentage = (actual_spent / budget.amount * 100) if budget.amount > 0 else 0

        if actual_spent < budget.amount:
            status = "within_budget"
        elif actual_spent == budget.amount:
            status = "on_budget"
        else:
            status = "over_budget"

        results.append({
            "category": budget.category,
            "budget": round(budget.amount, 2),
            "actual_spent": round(actual_spent, 2),
            "remaining": round(max(0, remaining), 2),
            "over_budget": round(over_budget, 2),
            "usage_percentage": round(usage_percentage, 2),
            "status": status
        })

        total_budget += budget.amount
        total_spent += actual_spent

    return {
        "month": month,
        "year": year,
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "total_remaining": round(max(0, total_budget - total_spent), 2),
        "categories": results
    }