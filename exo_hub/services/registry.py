import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import redis
import logging
from ..config import REDIS_URL
from ..models import Node, Task

logger = logging.getLogger(__name__)

class RedisRegistry:
    """Redis-based registry for managing nodes and tasks."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    # Node Management
    def register_node(self, node: Node) -> bool:
        """Register a new node."""
        try:
            node_key = f"node:{node.id}"
            node_data = {
                "id": node.id,
                "status": node.status,
                "capabilities": json.dumps(node.capabilities) if hasattr(node, 'capabilities') else "{}",
                "last_heartbeat": datetime.now().isoformat(),
                "registered_at": datetime.now().isoformat(),
                "tasks_completed": 0,
                "tasks_failed": 0
            }
            
            # Store node data
            self.redis_client.hset(node_key, mapping=node_data)
            
            # Add to active nodes set
            self.redis_client.sadd("active_nodes", node.id)
            
            # Set expiration for cleanup (24 hours)
            self.redis_client.expire(node_key, 86400)
            
            logger.info(f"Node {node.id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register node {node.id}: {e}")
            return False
    
    def update_node_heartbeat(self, node_id: str) -> bool:
        """Update node's last heartbeat timestamp."""
        try:
            node_key = f"node:{node_id}"
            if not self.redis_client.exists(node_key):
                logger.warning(f"Node {node_id} not found for heartbeat update")
                return False
            
            # Update heartbeat timestamp and status
            self.redis_client.hset(node_key, mapping={
                "last_heartbeat": datetime.now().isoformat(),
                "status": "online"
            })
            
            # Reset expiration
            self.redis_client.expire(node_key, 86400)
            
            logger.debug(f"Heartbeat updated for node {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat for node {node_id}: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node information."""
        try:
            node_key = f"node:{node_id}"
            node_data = self.redis_client.hgetall(node_key)
            
            if not node_data:
                return None
            
            # Check if node is offline (no heartbeat in last 30 seconds)
            last_heartbeat = datetime.fromisoformat(node_data.get("last_heartbeat", ""))
            if datetime.now() - last_heartbeat > timedelta(seconds=30):
                node_data["status"] = "offline"
                self.redis_client.hset(node_key, "status", "offline")
            
            return node_data
            
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get all registered nodes."""
        try:
            nodes = []
            node_ids = self.redis_client.smembers("active_nodes")
            
            for node_id in node_ids:
                node_data = self.get_node(node_id)
                if node_data:
                    nodes.append(node_data)
                else:
                    # Remove inactive node from set
                    self.redis_client.srem("active_nodes", node_id)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to get all nodes: {e}")
            return []
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from registry."""
        try:
            node_key = f"node:{node_id}"
            
            # Remove from active nodes set
            self.redis_client.srem("active_nodes", node_id)
            
            # Delete node data
            self.redis_client.delete(node_key)
            
            logger.info(f"Node {node_id} removed from registry")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove node {node_id}: {e}")
            return False
    
    # Task Management
    def create_task(self, task: Task) -> bool:
        """Create a new task."""
        try:
            task_key = f"task:{task.id}"
            task_data = {
                "id": task.id,
                "status": task.status,
                "model": getattr(task, 'model', ''),
                "input_data": json.dumps(getattr(task, 'input_data', {})),
                "node_id": getattr(task, 'node_id', ''),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "priority": getattr(task, 'priority', 1)
            }
            
            # Store task data
            self.redis_client.hset(task_key, mapping=task_data)
            
            # Add to pending tasks queue
            if task.status == "pending":
                priority = getattr(task, 'priority', 1)
                self.redis_client.zadd("pending_tasks", {task.id: priority})
            
            # Add to all tasks set
            self.redis_client.sadd("all_tasks", task.id)
            
            logger.info(f"Task {task.id} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create task {task.id}: {e}")
            return False
    
    def update_task_status(self, task_id: str, status: str, node_id: str = None, result: Any = None) -> bool:
        """Update task status and other fields."""
        try:
            task_key = f"task:{task_id}"
            if not self.redis_client.exists(task_key):
                logger.warning(f"Task {task_id} not found for status update")
                return False
            
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if node_id:
                update_data["node_id"] = node_id
            
            if result is not None:
                update_data["result"] = json.dumps(result)
            
            if status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()
            
            # Update task data
            self.redis_client.hset(task_key, mapping=update_data)
            
            # Move task between queues based on status
            if status == "running":
                self.redis_client.zrem("pending_tasks", task_id)
                self.redis_client.sadd("running_tasks", task_id)
            elif status == "completed":
                self.redis_client.srem("running_tasks", task_id)
                self.redis_client.sadd("completed_tasks", task_id)
                # Update node task completion count
                if node_id:
                    node_key = f"node:{node_id}"
                    self.redis_client.hincrby(node_key, "tasks_completed", 1)
            elif status == "failed":
                self.redis_client.srem("running_tasks", task_id)
                self.redis_client.sadd("failed_tasks", task_id)
                # Update node task failure count
                if node_id:
                    node_key = f"node:{node_id}"
                    self.redis_client.hincrby(node_key, "tasks_failed", 1)
            
            logger.info(f"Task {task_id} status updated to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information."""
        try:
            task_key = f"task:{task_id}"
            task_data = self.redis_client.hgetall(task_key)
            
            if not task_data:
                return None
            
            # Parse JSON fields
            if 'input_data' in task_data:
                try:
                    task_data['input_data'] = json.loads(task_data['input_data'])
                except json.JSONDecodeError:
                    task_data['input_data'] = {}
            
            if 'result' in task_data:
                try:
                    task_data['result'] = json.loads(task_data['result'])
                except json.JSONDecodeError:
                    task_data['result'] = None
            
            return task_data
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    def get_pending_task(self) -> Optional[str]:
        """Get the next pending task (highest priority)."""
        try:
            # Get highest priority task from sorted set
            tasks = self.redis_client.zrevrange("pending_tasks", 0, 0)
            if tasks:
                task_id = tasks[0]
                return task_id
            return None
            
        except Exception as e:
            logger.error(f"Failed to get pending task: {e}")
            return None
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all tasks with a specific status."""
        try:
            tasks = []
            
            if status == "pending":
                task_ids = self.redis_client.zrange("pending_tasks", 0, -1)
            elif status == "running":
                task_ids = self.redis_client.smembers("running_tasks")
            elif status == "completed":
                task_ids = self.redis_client.smembers("completed_tasks")
            elif status == "failed":
                task_ids = self.redis_client.smembers("failed_tasks")
            else:
                return []
            
            for task_id in task_ids:
                task_data = self.get_task(task_id)
                if task_data:
                    tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get tasks with status {status}: {e}")
            return []
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tasks (limited)."""
        try:
            tasks = []
            all_task_ids = list(self.redis_client.smembers("all_tasks"))[-limit:]
            
            for task_id in all_task_ids:
                task_data = self.get_task(task_id)
                if task_data:
                    tasks.append(task_data)
            
            # Sort by created_at (newest first)
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get all tasks: {e}")
            return []
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old completed/failed tasks."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0
            
            # Check completed and failed tasks
            for status in ["completed_tasks", "failed_tasks"]:
                task_ids = self.redis_client.smembers(status)
                
                for task_id in task_ids:
                    task_data = self.get_task(task_id)
                    if task_data and 'created_at' in task_data:
                        created_at = datetime.fromisoformat(task_data['created_at'])
                        if created_at < cutoff_date:
                            # Remove from all sets and delete task data
                            self.redis_client.srem(status, task_id)
                            self.redis_client.srem("all_tasks", task_id)
                            self.redis_client.delete(f"task:{task_id}")
                            cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old tasks")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        try:
            stats = {
                "nodes": {
                    "total": self.redis_client.scard("active_nodes"),
                    "online": 0,
                    "offline": 0
                },
                "tasks": {
                    "pending": self.redis_client.zcard("pending_tasks"),
                    "running": self.redis_client.scard("running_tasks"),
                    "completed": self.redis_client.scard("completed_tasks"),
                    "failed": self.redis_client.scard("failed_tasks"),
                    "total": self.redis_client.scard("all_tasks")
                }
            }
            
            # Count online/offline nodes
            nodes = self.get_all_nodes()
            for node in nodes:
                if node.get("status") == "online":
                    stats["nodes"]["online"] += 1
                else:
                    stats["nodes"]["offline"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"nodes": {"total": 0, "online": 0, "offline": 0}, "tasks": {"pending": 0, "running": 0, "completed": 0, "failed": 0, "total": 0}}

# Global registry instance
registry = RedisRegistry()
