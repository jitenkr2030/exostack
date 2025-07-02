from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from ..models import (
    NodeRegistrationRequest, 
    NodeHeartbeatRequest, 
    Node, 
    NodeCapabilities
)
from ..services.registry import registry
from ..services.logger import get_logger, log_node_event
import psutil
import platform
from datetime import datetime

router = APIRouter(prefix="/nodes", tags=["nodes"])
logger = get_logger(__name__)

@router.post("/register")
async def register_node(request: NodeRegistrationRequest):
    """Register a new node in the system."""
    try:
        # Create node object with system info if not provided
        capabilities = request.capabilities or NodeCapabilities()
        
        node = Node(
            id=request.id,
            status="online",
            capabilities=capabilities,
            host=request.host,
            port=request.port,
            version=request.version,
            registered_at=datetime.now()
        )
        
        # Register in Redis
        success = registry.register_node(node)
        
        if success:
            log_node_event(request.id, "registered", {
                "host": request.host,
                "port": request.port,
                "capabilities": capabilities.dict() if capabilities else None
            })
            
            return {
                "status": "registered",
                "node_id": request.id,
                "message": "Node successfully registered"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to register node")
            
    except Exception as e:
        logger.error(f"Node registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/heartbeat")
async def node_heartbeat(request: NodeHeartbeatRequest):
    """Receive heartbeat from a node."""
    try:
        success = registry.update_node_heartbeat(request.id)
        
        if success:
            # Update additional metrics if provided
            if request.current_load is not None or request.active_tasks is not None:
                node_key = f"node:{request.id}"
                update_data = {}
                if request.current_load is not None:
                    update_data["current_load"] = request.current_load
                if request.active_tasks is not None:
                    update_data["active_tasks"] = request.active_tasks
                
                registry.redis_client.hset(node_key, mapping=update_data)
            
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "message": "Heartbeat received"
            }
        else:
            raise HTTPException(status_code=404, detail="Node not found")
            
    except Exception as e:
        logger.error(f"Heartbeat processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_nodes_status() -> List[Dict[str, Any]]:
    """Get status of all registered nodes."""
    try:
        nodes = registry.get_all_nodes()
        return nodes
    except Exception as e:
        logger.error(f"Failed to get nodes status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{node_id}")
async def get_node_info(node_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific node."""
    try:
        node = registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{node_id}")
async def remove_node(node_id: str):
    """Remove a node from the system."""
    try:
        success = registry.remove_node(node_id)
        if success:
            log_node_event(node_id, "removed")
            return {"status": "removed", "node_id": node_id}
        else:
            raise HTTPException(status_code=404, detail="Node not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{node_id}/health")
async def get_node_health(node_id: str):
    """Get health metrics for a specific node."""
    try:
        node = registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Calculate health metrics
        last_heartbeat = datetime.fromisoformat(node.get("last_heartbeat", ""))
        time_since_heartbeat = (datetime.now() - last_heartbeat).total_seconds()
        
        health_status = {
            "node_id": node_id,
            "status": node.get("status", "unknown"),
            "last_heartbeat": node.get("last_heartbeat"),
            "seconds_since_heartbeat": time_since_heartbeat,
            "current_load": float(node.get("current_load", 0)),
            "active_tasks": int(node.get("active_tasks", 0)),
            "tasks_completed": int(node.get("tasks_completed", 0)),
            "tasks_failed": int(node.get("tasks_failed", 0)),
            "health_score": _calculate_health_score(node, time_since_heartbeat)
        }
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_health_score(node: Dict[str, Any], time_since_heartbeat: float) -> float:
    """Calculate a health score for the node (0-100)."""
    score = 100.0
    
    # Penalize for old heartbeats
    if time_since_heartbeat > 30:  # 30 seconds
        score -= min(50, time_since_heartbeat - 30)
    
    # Penalize for high load
    current_load = float(node.get("current_load", 0))
    if current_load > 0.8:
        score -= (current_load - 0.8) * 100
    
    # Penalize for task failures
    tasks_completed = int(node.get("tasks_completed", 0))
    tasks_failed = int(node.get("tasks_failed", 0))
    total_tasks = tasks_completed + tasks_failed
    
    if total_tasks > 0:
        failure_rate = tasks_failed / total_tasks
        score -= failure_rate * 30
    
    return max(0.0, min(100.0, score))
