from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.goal import Goal
from models.user import User
from routers.auth import get_current_user
from schemas.goal_schema import GoalCreate, GoalUpdate

router = APIRouter(prefix="/goals", tags=["Goals"])


def build_goal_response(goal: Goal):
    progress_percentage = 0
    if goal.target_amount > 0:
        progress_percentage = (goal.current_amount / goal.target_amount) * 100

    remaining_amount = goal.target_amount - goal.current_amount

    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": round(goal.target_amount, 2),
        "current_amount": round(goal.current_amount, 2),
        "target_date": goal.target_date,
        "progress_percentage": round(progress_percentage, 2),
        "remaining_amount": round(remaining_amount, 2)
    }


@router.post("/")
def create_goal(
    data: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = Goal(
        name=data.name,
        target_amount=data.target_amount,
        current_amount=data.current_amount,
        target_date=data.target_date,
        user_id=current_user.id
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return build_goal_response(goal)


@router.get("/")
def get_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goals = (
        db.query(Goal)
        .filter(Goal.user_id == current_user.id)
        .order_by(Goal.target_date.asc(), Goal.id.asc())
        .all()
    )
    return [build_goal_response(goal) for goal in goals]


@router.get("/{goal_id}")
def get_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == current_user.id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return build_goal_response(goal)


@router.put("/{goal_id}")
def update_goal(
    goal_id: int,
    data: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == current_user.id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.name = data.name
    goal.target_amount = data.target_amount
    goal.current_amount = data.current_amount
    goal.target_date = data.target_date

    db.commit()
    db.refresh(goal)

    return build_goal_response(goal)


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == current_user.id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.delete(goal)
    db.commit()

    return {"message": "Goal deleted successfully"}