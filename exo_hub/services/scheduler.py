import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..models import Task
from .registry import registry
import requests

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Task scheduler that manages task distribution to nodes."""
    
    def __init__(self):
        self.running = False
        self.scheduler_task = None
    
    async def start(self):
        """Start the task scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")
    
    async def stop(self):
        """Stop the task scheduler."""
        if not self.running:
            return
        
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                await self._process_pending_tasks()
                await self._check_running_tasks()
                await self._cleanup_old_tasks()
                
                # Wait before next iteration
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _process_pending_tasks(self):
        """Process pending tasks and assign them to available nodes."""
        try:
            # Get available nodes
            available_nodes = self._get_available_nodes()
            if not available_nodes:
                logger.debug("No available nodes for task assignment")
                return
            
            # Process pending tasks
            for node in available_nodes:
                if not self.running:
                    break
                
                # Get next pending task
                task_id = registry.get_pending_task()
                if not task_id:
                    break  # No more pending tasks
                
                # Assign task to node
                await self._assign_task_to_node(task_id, node)
                
        except Exception as e:
            logger.error(f"Error processing pending tasks: {e}")
    
    def _get_available_nodes(self) -> List[Dict[str, Any]]:
        """Get list of available nodes that can accept new tasks."""
        try:
            all_nodes = registry.get_all_nodes()
            available_nodes = []
            
            for node in all_nodes:
                if node.get("status") == "online":
                    # Check if node has capacity for more tasks
                    running_tasks = len(registry.get_tasks_by_status("running"))
                    node_tasks = [t for t in registry.get_tasks_by_status("running") 
                                 if t.get("node_id") == node["id"]]
                    
                    # Simple capacity check - max 3 concurrent tasks per node
                    if len(node_tasks) < 3:
                        available_nodes.append(node)
            
            return available_nodes
            
        except Exception as e:
            logger.error(f"Error getting available nodes: {e}")
            return []
    
    async def _assign_task_to_node(self, task_id: str, node: Dict[str, Any]):
        """Assign a specific task to a specific node."""
        try:
            task_data = registry.get_task(task_id)
            if not task_data:
                logger.warning(f"Task {task_id} not found for assignment")
                return
            
            node_id = node["id"]
            
            # Update task status to running
            success = registry.update_task_status(task_id, "running", node_id)
            if not success:
                logger.error(f"Failed to update task {task_id} status to running")
                return
            
            # Send task to node (async HTTP request)
            await self._send_task_to_node(task_id, task_data, node)
            
            logger.info(f"Task {task_id} assigned to node {node_id}")
            
        except Exception as e:
            logger.error(f"Error assigning task {task_id} to node {node['id']}: {e}")
            # Revert task status back to pending
            registry.update_task_status(task_id, "pending")
    
    async def _send_task_to_node(self, task_id: str, task_data: Dict[str, Any], node: Dict[str, Any]):
        """Send task to node for execution."""
        try:
            # For now, we'll simulate sending the task
            # In a real implementation, you'd make an HTTP request to the node
            
            # Simulate task execution time
            await asyncio.sleep(0.1)
            
            # For demo purposes, randomly succeed or fail
            import random
            if random.random() > 0.1:  # 90% success rate
                # Simulate successful completion
                result = {
                    "output": f"Processed task {task_id} on node {node['id']}",
                    "processing_time": random.uniform(1.0, 10.0),
                    "tokens_generated": random.randint(50, 500)
                }
                registry.update_task_status(task_id, "completed", node["id"], result)
            else:
                # Simulate failure
                registry.update_task_status(task_id, "failed", node["id"], 
                                          {"error": "Simulated task failure"})
            
            logger.debug(f"Task {task_id} sent to node {node['id']}")
            
        except Exception as e:
            logger.error(f"Error sending task {task_id} to node {node['id']}: {e}")
            # Mark task as failed
            registry.update_task_status(task_id, "failed", node["id"], 
                                      {"error": str(e)})
    
    async def _check_running_tasks(self):
        """Check running tasks for timeouts or completion."""
        try:
            running_tasks = registry.get_tasks_by_status("running")
            
            for task in running_tasks:
                if not self.running:
                    break
                
                # Check for task timeout (e.g., 5 minutes)
                created_at = datetime.fromisoformat(task.get("created_at", ""))
                if (datetime.now() - created_at).total_seconds() > 300:  # 5 minutes
                    logger.warning(f"Task {task['id']} timed out")
                    registry.update_task_status(task["id"], "failed", 
                                              task.get("node_id"), 
                                              {"error": "Task timeout"})
                
        except Exception as e:
            logger.error(f"Error checking running tasks: {e}")
    
    async def _cleanup_old_tasks(self):
        """Periodically cleanup old completed/failed tasks."""
        try:
            # Run cleanup every hour (3600 / 5 = 720 iterations)
            if not hasattr(self, '_cleanup_counter'):
                self._cleanup_counter = 0
            
            self._cleanup_counter += 1
            if self._cleanup_counter >= 720:  # Every hour
                cleaned_count = registry.cleanup_old_tasks(days=7)
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} old tasks")
                self._cleanup_counter = 0
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def create_task(self, model: str, input_data: Dict[str, Any], priority: int = 1) -> str:
        """Create a new task."""
        try:
            task_id = str(uuid.uuid4())
            
            # Create task object
            task = Task(
                id=task_id,
                status="pending",
                model=model,
                input_data=input_data,
                priority=priority
            )
            
            # Store in registry
            success = registry.create_task(task)
            if success:
                logger.info(f"Created new task {task_id} with model {model}")
                return task_id
            else:
                logger.error(f"Failed to create task {task_id}")
                raise Exception("Failed to create task")
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and details."""
        return registry.get_task(task_id)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return registry.get_stats()
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tasks."""
        return registry.get_all_tasks(limit)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        try:
            task = registry.get_task(task_id)
            if not task:
                return False
            
            if task.get("status") == "pending":
                registry.update_task_status(task_id, "failed", None, 
                                          {"error": "Task cancelled by user"})
                logger.info(f"Task {task_id} cancelled")
                return True
            else:
                logger.warning(f"Cannot cancel task {task_id} with status {task.get('status')}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

# Global scheduler instance
scheduler = TaskScheduler()
