import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def register_agent(agent_id: str, hub_url: str) -> bool:
    """Register agent with the hub.
    
    Args:
        agent_id: Unique identifier for the agent
        hub_url: URL of the hub to register with
        
    Returns:
        bool: True if registration successful, False otherwise
    """
    try:
        response = requests.post(
            f"{hub_url}/nodes/register", 
            json={"id": agent_id},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Agent {agent_id} registered successfully")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to register agent {agent_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during agent registration: {e}")
        return False

def heartbeat(agent_id: str, hub_url: str) -> bool:
    """Send heartbeat to the hub.
    
    Args:
        agent_id: Unique identifier for the agent
        hub_url: URL of the hub to send heartbeat to
        
    Returns:
        bool: True if heartbeat successful, False otherwise
    """
    try:
        response = requests.post(
            f"{hub_url}/nodes/heartbeat", 
            json={"id": agent_id},
            timeout=5
        )
        response.raise_for_status()
        logger.debug(f"Heartbeat sent for agent {agent_id}")
        return True
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to send heartbeat for agent {agent_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during heartbeat: {e}")
        return False
