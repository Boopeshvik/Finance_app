import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine

from routers.auth import router as auth_router
from routers.transactions import router as transactions_router
from routers.plans import router as plans_router
from routers.assets import router as assets_router
from routers.liabilities import router as liabilities_router
from routers.networth import router as networth_router
from routers.goals import router as goals_router
from routers.score import router as score_router
from routers.dashboard import router as dashboard_router
from routers.budgets import router as budgets_router
from routers.categories import router as categories_router
from routers.ai import router as ai_router

from models.user import User
from models.transaction import Transaction
from models.monthly_plan import MonthlyPlan
from models.yearly_plan import YearlyPlan
from models.asset import Asset
from models.liability import Liability
from models.goal import Goal
from models.budget import Budget
from models.category import Category

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Finance Tracker API")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(plans_router)
app.include_router(assets_router)
app.include_router(liabilities_router)
app.include_router(networth_router)
app.include_router(goals_router)
app.include_router(score_router)
app.include_router(dashboard_router)
app.include_router(budgets_router)
app.include_router(categories_router)
app.include_router(ai_router)


@app.get("/")
def home():
    return {"message": "Personal Finance Tracker API is running"}