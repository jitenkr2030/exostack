from fastapi import FastAPI
from .routers import nodes, tasks, status
from .services.logger import get_logger

logger = get_logger(__name__)

app = FastAPI()
app.include_router(nodes.router)
app.include_router(tasks.router)
app.include_router(status.router)

@app.on_event("startup")
async def startup_event():
    logger.info("ExoHub is starting up.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("ExoHub is shutting down.")

# Custom middleware for logging requests
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code} from {request.url.path}")
    return response
