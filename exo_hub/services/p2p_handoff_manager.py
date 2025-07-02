"""
P2P Inference Handoff System
Enables agents to delegate tasks to other agents directly for load balancing and optimization.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from ..models import Task, TaskResult
from .registry import registry
from .logger import get_logger, log_task_event

logger = get_logger(__name__)

class P2PHandoffManager:
    """Manages peer-to-peer task handoffs between agents."""
    
    def __init__(self):
        self.active_handoffs: Dict[str, Dict] = {}  # task_id -> handoff_info
        self.agent_capabilities: Dict[str, Dict] = {}  # agent_id -> capabilities
        self.handoff_history: List[Dict] = []
    
    async def evaluate_handoff_candidate(self, task_id: str, current_agent_id: str) -> Optional[str]:
        """
        Evaluate if a task should be handed off to another agent.
        Returns the best candidate agent ID or None.
        """
        try:
            # Get current task details
            task = registry.get_task(task_id)
            if not task:
                return None
            
            # Get current agent info
            current_agent = registry.get_node(current_agent_id)
            if not current_agent:
                return None
            
            # Get all online agents
            all_agents = registry.get_all_nodes()
            online_agents = [agent for agent in all_agents if agent.get("status") == "online"]
            
            # Filter out current agent and agents that are overloaded
            candidate_agents = []
            for agent in online_agents:
                if agent["id"] == current_agent_id:
                    continue
                
                # Check load and capacity
                current_load = float(agent.get("current_load", 0))
                active_tasks = int(agent.get("active_tasks", 0))
                
                if current_load < 0.7 and active_tasks < 3:  # Available capacity
                    candidate_agents.append(agent)
            
            if not candidate_agents:
                return None
            
            # Score candidates based on various factors
            best_candidate = self._score_candidates(
                task, current_agent, candidate_agents
            )
            
            return best_candidate["id"] if best_candidate else None
            
        except Exception as e:
            logger.error(f"Error evaluating handoff candidate: {e}")
            return None
    
    def _score_candidates(self, task: Dict, current_agent: Dict, candidates: List[Dict]) -> Optional[Dict]:
        """Score and rank candidate agents for task handoff."""
        scored_candidates = []
        
        for candidate in candidates:
            score = 0
            
            # Factor 1: Load (lower is better)
            load = float(candidate.get("current_load", 1.0))
            score += (1.0 - load) * 40  # Up to 40 points
            
            # Factor 2: Active tasks (fewer is better)
            active_tasks = int(candidate.get("active_tasks", 99))
            score += max(0, (5 - active_tasks)) * 10  # Up to 50 points
            
            # Factor 3: Success rate (higher is better)
            completed = int(candidate.get("tasks_completed", 0))
            failed = int(candidate.get("tasks_failed", 0))
            total = completed + failed
            if total > 0:
                success_rate = completed / total
                score += success_rate * 30  # Up to 30 points
            
            # Factor 4: Model compatibility (if we have capability info)
            model_name = task.get("model", "")
            if self._supports_model(candidate["id"], model_name):
                score += 20
            
            scored_candidates.append({"agent": candidate, "score": score})
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Return best candidate if score is significantly better
        if scored_candidates and scored_candidates[0]["score"] > 50:
            return scored_candidates[0]["agent"]
        
        return None
    
    def _supports_model(self, agent_id: str, model_name: str) -> bool:
        """Check if an agent supports a specific model."""
        capabilities = self.agent_capabilities.get(agent_id, {})
        supported_models = capabilities.get("supported_models", [])
        return model_name in supported_models or len(supported_models) == 0
    
    async def initiate_handoff(self, task_id: str, from_agent: str, to_agent: str) -> bool:
        """
        Initiate a task handoff from one agent to another.
        """
        try:
            # Get task details
            task = registry.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found for handoff")
                return False
            
            # Get target agent details
            target_agent = registry.get_node(to_agent)
            if not target_agent or target_agent.get("status") != "online":
                logger.error(f"Target agent {to_agent} not available for handoff")
                return False
            
            # Create handoff record
            handoff_info = {
                "task_id": task_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "initiated_at": datetime.now().isoformat(),
                "status": "pending"
            }
            
            self.active_handoffs[task_id] = handoff_info
            
            # Notify target agent about the handoff
            success = await self._notify_agent_handoff(to_agent, task_id, task)
            
            if success:
                # Update task assignment
                registry.update_task_status(task_id, "running", to_agent)
                
                # Update handoff status
                handoff_info["status"] = "completed"
                handoff_info["completed_at"] = datetime.now().isoformat()
                
                # Record in history
                self.handoff_history.append(handoff_info.copy())
                
                log_task_event(task_id, "handed_off", to_agent, {
                    "from_agent": from_agent,
                    "to_agent": to_agent
                })
                
                logger.info(f"Task {task_id} successfully handed off from {from_agent} to {to_agent}")
                return True
            else:
                handoff_info["status"] = "failed"
                logger.error(f"Failed to notify agent {to_agent} about handoff")
                return False
                
        except Exception as e:
            logger.error(f"Error during task handoff: {e}")
            return False
        finally:
            # Clean up active handoff record
            if task_id in self.active_handoffs:
                del self.active_handoffs[task_id]
    
    async def _notify_agent_handoff(self, agent_id: str, task_id: str, task_data: Dict) -> bool:
        """Notify an agent about an incoming task handoff."""
        try:
            agent = registry.get_node(agent_id)
            if not agent:
                return False
            
            # If agent has host/port, send direct HTTP notification
            if agent.get("host") and agent.get("port"):
                agent_url = f"http://{agent['host']}:{agent['port']}"
                
                notification_data = {
                    "type": "task_handoff",
                    "task_id": task_id,
                    "task_data": task_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                try:
                    response = requests.post(
                        f"{agent_url}/handoff/receive",
                        json=notification_data,
                        timeout=10
                    )
                    return response.status_code == 200
                except requests.RequestException as e:
                    logger.warning(f"Direct notification to {agent_id} failed: {e}")
            
            # Fallback: Use Redis for notification
            notification_key = f"handoff_notification:{agent_id}"
            notification_data = {
                "task_id": task_id,
                "task_data": task_data,
                "timestamp": datetime.now().isoformat()
            }
            
            registry.redis_client.lpush(
                notification_key, 
                json.dumps(notification_data)
            )
            registry.redis_client.expire(notification_key, 300)  # 5 minutes
            
            return True
            
        except Exception as e:
            logger.error(f"Error notifying agent {agent_id}: {e}")
            return False
    
    def check_pending_handoffs(self, agent_id: str) -> List[Dict]:
        """Check for pending handoff notifications for an agent."""
        try:
            notification_key = f"handoff_notification:{agent_id}"
            notifications = []
            
            # Get all pending notifications
            while True:
                notification_data = registry.redis_client.rpop(notification_key)
                if not notification_data:
                    break
                
                try:
                    notification = json.loads(notification_data)
                    notifications.append(notification)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid notification data for {agent_id}")
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error checking handoff notifications for {agent_id}: {e}")
            return []
    
    def update_agent_capabilities(self, agent_id: str, capabilities: Dict):
        """Update an agent's capabilities for better handoff decisions."""
        self.agent_capabilities[agent_id] = capabilities
        logger.debug(f"Updated capabilities for agent {agent_id}")
    
    def get_handoff_stats(self) -> Dict[str, Any]:
        """Get statistics about handoff operations."""
        total_handoffs = len(self.handoff_history)
        if total_handoffs == 0:
            return {
                "total_handoffs": 0,
                "success_rate": 0,
                "average_handoffs_per_hour": 0
            }
        
        successful_handoffs = len([
            h for h in self.handoff_history 
            if h.get("status") == "completed"
        ])
        
        success_rate = (successful_handoffs / total_handoffs) * 100
        
        # Calculate handoffs per hour (last 24 hours)
        now = datetime.now()
        recent_handoffs = [
            h for h in self.handoff_history
            if (now - datetime.fromisoformat(h["initiated_at"])).total_seconds() < 86400
        ]
        
        handoffs_per_hour = len(recent_handoffs) / 24
        
        return {
            "total_handoffs": total_handoffs,
            "successful_handoffs": successful_handoffs,
            "success_rate": round(success_rate, 2),
            "active_handoffs": len(self.active_handoffs),
            "average_handoffs_per_hour": round(handoffs_per_hour, 2),
            "recent_handoffs": recent_handoffs[-10:]  # Last 10 handoffs
        }

# Global P2P handoff manager instance
p2p_manager = P2PHandoffManager()
