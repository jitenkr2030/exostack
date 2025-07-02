import time
import logging
from .config import AGENT_ID, HUB_URL
from .executor import run_inference
from .utils import heartbeat, register_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main_loop():
    """Main agent loop with error handling."""
    logger.info(f"[Agent] Starting agent with ID: {AGENT_ID}")
    
    # Try to register with retries
    max_retries = 3
    for attempt in range(max_retries):
        if register_agent(AGENT_ID, HUB_URL):
            logger.info("[Agent] Successfully registered with hub")
            break
        elif attempt < max_retries - 1:
            logger.warning(f"[Agent] Registration attempt {attempt + 1} failed, retrying...")
            time.sleep(5)
        else:
            logger.error("[Agent] Failed to register after all attempts, continuing anyway...")
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    while True:
        try:
            logger.debug("[Agent] Sending heartbeat...")
            if heartbeat(AGENT_ID, HUB_URL):
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"[Agent] {consecutive_failures} consecutive heartbeat failures, attempting to re-register...")
                    register_agent(AGENT_ID, HUB_URL)
                    consecutive_failures = 0
            
            logger.debug("[Agent] Running inference...")
            run_inference()
            
        except KeyboardInterrupt:
            logger.info("[Agent] Received shutdown signal, exiting gracefully...")
            break
        except Exception as e:
            logger.error(f"[Agent] Unexpected error in main loop: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    main_loop()
