from fastapi import FastAPI
from .routers import nodes, tasks, status

app = FastAPI()
app.include_router(nodes.router)
app.include_router(tasks.router)
app.include_router(status.router)
