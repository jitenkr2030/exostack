from fastapi import APIRouter

router = APIRouter(prefix="/tasks")

@router.get("/next")
def get_next_task():
    return {"task": "run_model_x"}
