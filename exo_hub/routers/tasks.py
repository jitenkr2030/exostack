from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from ..models import (
    TaskCreationRequest,
    TaskUpdateRequest, 
    Task,
    TaskInput,
    TaskResult,
    TaskStatus
)
from ..services.scheduler import scheduler
from ..services.registry import registry
from ..services.logger import get_logger, log_task_event
from datetime import datetime
import asyncio

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)

@router.post("/create")
async def create_task(request: TaskCreationRequest, background_tasks: BackgroundTasks):
    """Create a new inference task."""
    try:
        task_id = scheduler.create_task(
            model=request.model,
            input_data=request.input_data.dict(),
            priority=request.priority
        )
        
        log_task_event(task_id, "created", details={
            "model": request.model,
            "priority": request.priority
        })
        
        return {
            "task_id": task_id,
            "status": "created",
            "message": "Task created successfully"
        }
        
    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get task status and details."""
    try:
        task = scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{task_id}/status")
async def update_task_status(task_id: str, request: TaskUpdateRequest):
    """Update task status (usually called by agents)."""
    try:
        result_data = request.result.dict() if request.result else None
        
        success = registry.update_task_status(
            task_id=task_id,
            status=request.status.value,
            result=result_data
        )
        
        if success:
            log_task_event(task_id, f"status_updated_to_{request.status.value}")
            return {"status": "updated", "task_id": task_id}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_tasks_status(limit: int = 100) -> List[Dict[str, Any]]:
    """Get status of all tasks."""
    try:
        tasks = scheduler.get_all_tasks(limit)
        return tasks
    except Exception as e:
        logger.error(f"Failed to get tasks status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending task."""
    try:
        success = scheduler.cancel_task(task_id)
        if success:
            log_task_event(task_id, "cancelled")
            return {"status": "cancelled", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="Cannot cancel task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/pending")
async def get_pending_tasks() -> List[Dict[str, Any]]:
    """Get all pending tasks in the queue."""
    try:
        tasks = registry.get_tasks_by_status("pending")
        return tasks
    except Exception as e:
        logger.error(f"Failed to get pending tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/running")
async def get_running_tasks() -> List[Dict[str, Any]]:
    """Get all currently running tasks."""
    try:
        tasks = registry.get_tasks_by_status("running")
        return tasks
    except Exception as e:
        logger.error(f"Failed to get running tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
async def create_batch_tasks(requests: List[TaskCreationRequest]):
    """Create multiple tasks in batch."""
    try:
        task_ids = []
        for request in requests:
            task_id = scheduler.create_task(
                model=request.model,
                input_data=request.input_data.dict(),
                priority=request.priority
            )
            task_ids.append(task_id)
            
            log_task_event(task_id, "created_in_batch", details={
                "model": request.model,
                "batch_size": len(requests)
            })
        
        return {
            "task_ids": task_ids,
            "status": "created",
            "count": len(task_ids)
        }
        
    except Exception as e:
        logger.error(f"Batch task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/{node_id}/next")
async def get_next_task_for_agent(node_id: str) -> Optional[Dict[str, Any]]:
    """Get the next task for a specific agent."""
    try:
        # Verify agent exists and is online
        node = registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if node.get("status") != "online":
            raise HTTPException(status_code=400, detail="Agent is not online")
        
        # Get next pending task
        task_id = registry.get_pending_task()
        if not task_id:
            return {"message": "No pending tasks"}
        
        # Get full task details
        task = registry.get_task(task_id)
        if task:
            # Mark as assigned to this agent
            registry.update_task_status(task_id, "running", node_id)
            log_task_event(task_id, "assigned", node_id, {"agent": node_id})
            
            return {
                "task_id": task_id,
                "task_data": task,
                "assigned_to": node_id
            }
        else:
            return {"message": "No pending tasks"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get next task for agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/{node_id}/complete/{task_id}")
async def complete_task_for_agent(node_id: str, task_id: str, result: TaskResult):
    """Mark a task as completed by an agent."""
    try:
        # Verify the task is assigned to this agent
        task = registry.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get("node_id") != node_id:
            raise HTTPException(status_code=403, detail="Task not assigned to this agent")
        
        # Update task status
        success = registry.update_task_status(
            task_id=task_id,
            status="completed",
            node_id=node_id,
            result=result.dict()
        )
        
        if success:
            log_task_event(task_id, "completed", node_id, {
                "processing_time": result.processing_time,
                "tokens_generated": result.tokens_generated
            })
            
            return {
                "status": "completed",
                "task_id": task_id,
                "agent": node_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update task")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/{node_id}/fail/{task_id}")
async def fail_task_for_agent(node_id: str, task_id: str, error: str):
    """Mark a task as failed by an agent."""
    try:
        # Verify the task is assigned to this agent
        task = registry.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get("node_id") != node_id:
            raise HTTPException(status_code=403, detail="Task not assigned to this agent")
        
        # Update task status
        success = registry.update_task_status(
            task_id=task_id,
            status="failed",
            node_id=node_id,
            result={"error": error}
        )
        
        if success:
            log_task_event(task_id, "failed", node_id, {"error": error})
            
            return {
                "status": "failed",
                "task_id": task_id,
                "agent": node_id,
                "error": error
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update task")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fail task: {e}")
        raise HTTPException(status_code=500, detail=str(e))
