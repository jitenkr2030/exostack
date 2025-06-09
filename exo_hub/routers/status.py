from fastapi import APIRouter

router = APIRouter(prefix="/status")

@router.get("/health")
def health_check():
    return {"status": "ok"}
