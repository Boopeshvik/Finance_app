from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract

from database import get_db
from models.monthly_plan import MonthlyPlan
from models.yearly_plan import YearlyPlan
from models.transaction import Transaction
from schemas.monthly_plan_schema import MonthlyPlanCreate, MonthlyPlanResponse
from schemas.yearly_plan_schema import YearlyPlanCreate, YearlyPlanResponse

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post("/monthly", response_model=MonthlyPlanResponse)
def create_monthly_plan(data: MonthlyPlanCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(MonthlyPlan)
        .filter(MonthlyPlan.month == data.month, MonthlyPlan.year == data.year)
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Monthly plan already exists for this month and year")

    plan = MonthlyPlan(
        month=data.month,
        year=data.year,
        planned_income=data.planned_income,
        planned_expense=data.planned_expense,
        planned_savings=data.planned_savings
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/monthly/{year}/{month}")
def get_monthly_plan_vs_actual(year: int, month: int, db: Session = Depends(get_db)):
    plan = (
        db.query(MonthlyPlan)
        .filter(MonthlyPlan.month == month, MonthlyPlan.year == year)
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Monthly plan not found")

    transactions = (
        db.query(Transaction)
        .filter(extract("month", Transaction.date) == month)
        .filter(extract("year", Transaction.date) == year)
        .all()
    )

    actual_income = sum(t.amount for t in transactions if t.type == "income")
    actual_expense = sum(t.amount for t in transactions if t.type == "expense")
    actual_savings = actual_income - actual_expense

    return {
        "month": month,
        "year": year,
        "planned": {
            "income": round(plan.planned_income, 2),
            "expense": round(plan.planned_expense, 2),
            "savings": round(plan.planned_savings, 2)
        },
        "actual": {
            "income": round(actual_income, 2),
            "expense": round(actual_expense, 2),
            "savings": round(actual_savings, 2)
        },
        "difference": {
            "income": round(actual_income - plan.planned_income, 2),
            "expense": round(actual_expense - plan.planned_expense, 2),
            "savings": round(actual_savings - plan.planned_savings, 2)
        }
    }


@router.put("/monthly/{plan_id}", response_model=MonthlyPlanResponse)
def update_monthly_plan(plan_id: int, data: MonthlyPlanCreate, db: Session = Depends(get_db)):
    plan = db.query(MonthlyPlan).filter(MonthlyPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Monthly plan not found")

    duplicate = (
        db.query(MonthlyPlan)
        .filter(
            MonthlyPlan.month == data.month,
            MonthlyPlan.year == data.year,
            MonthlyPlan.id != plan_id
        )
        .first()
    )

    if duplicate:
        raise HTTPException(status_code=400, detail="Another monthly plan already exists for this month and year")

    plan.month = data.month
    plan.year = data.year
    plan.planned_income = data.planned_income
    plan.planned_expense = data.planned_expense
    plan.planned_savings = data.planned_savings

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/monthly/{plan_id}")
def delete_monthly_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(MonthlyPlan).filter(MonthlyPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Monthly plan not found")

    db.delete(plan)
    db.commit()

    return {"message": "Monthly plan deleted successfully"}


@router.post("/yearly", response_model=YearlyPlanResponse)
def create_yearly_plan(data: YearlyPlanCreate, db: Session = Depends(get_db)):
    existing = db.query(YearlyPlan).filter(YearlyPlan.year == data.year).first()

    if existing:
        raise HTTPException(status_code=400, detail="Yearly plan already exists for this year")

    plan = YearlyPlan(
        year=data.year,
        planned_income=data.planned_income,
        planned_expense=data.planned_expense,
        planned_savings=data.planned_savings
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/yearly/{year}")
def get_yearly_plan_vs_actual(year: int, db: Session = Depends(get_db)):
    plan = db.query(YearlyPlan).filter(YearlyPlan.year == year).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Yearly plan not found")

    transactions = (
        db.query(Transaction)
        .filter(extract("year", Transaction.date) == year)
        .all()
    )

    actual_income = sum(t.amount for t in transactions if t.type == "income")
    actual_expense = sum(t.amount for t in transactions if t.type == "expense")
    actual_savings = actual_income - actual_expense

    today = date.today()

    if year < today.year:
        months_passed = 12
    elif year == today.year:
        months_passed = today.month
    else:
        months_passed = 0

    if months_passed > 0:
        forecast_income = (actual_income / months_passed) * 12
        forecast_expense = (actual_expense / months_passed) * 12
        forecast_savings = (actual_savings / months_passed) * 12
    else:
        forecast_income = 0
        forecast_expense = 0
        forecast_savings = 0

    return {
        "year": year,
        "planned": {
            "income": round(plan.planned_income, 2),
            "expense": round(plan.planned_expense, 2),
            "savings": round(plan.planned_savings, 2)
        },
        "so_far": {
            "income": round(actual_income, 2),
            "expense": round(actual_expense, 2),
            "savings": round(actual_savings, 2)
        },
        "forecast": {
            "income": round(forecast_income, 2),
            "expense": round(forecast_expense, 2),
            "savings": round(forecast_savings, 2)
        },
        "difference_vs_plan": {
            "income": round(forecast_income - plan.planned_income, 2),
            "expense": round(forecast_expense - plan.planned_expense, 2),
            "savings": round(forecast_savings - plan.planned_savings, 2)
        }
    }


@router.put("/yearly/{plan_id}", response_model=YearlyPlanResponse)
def update_yearly_plan(plan_id: int, data: YearlyPlanCreate, db: Session = Depends(get_db)):
    plan = db.query(YearlyPlan).filter(YearlyPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Yearly plan not found")

    duplicate = (
        db.query(YearlyPlan)
        .filter(YearlyPlan.year == data.year, YearlyPlan.id != plan_id)
        .first()
    )

    if duplicate:
        raise HTTPException(status_code=400, detail="Another yearly plan already exists for this year")

    plan.year = data.year
    plan.planned_income = data.planned_income
    plan.planned_expense = data.planned_expense
    plan.planned_savings = data.planned_savings

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/yearly/{plan_id}")
def delete_yearly_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(YearlyPlan).filter(YearlyPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Yearly plan not found")

    db.delete(plan)
    db.commit()

    return {"message": "Yearly plan deleted successfully"}