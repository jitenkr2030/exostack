from fastapi import APIRouter

router = APIRouter(prefix="/nodes")

@router.post("/register")
def register_node(data: dict):
    return {"message": "Node registered", "data": data}

@router.post("/heartbeat")
def heartbeat(data: dict):
    return {"message": "Heartbeat received", "data": data}
