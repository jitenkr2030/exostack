import time
from .config import AGENT_ID, HUB_URL
from .executor import run_inference
from .utils import heartbeat, register_agent

def main_loop():
    print(f"[Agent] Starting agent with ID: {AGENT_ID}")
    register_agent(AGENT_ID, HUB_URL)
    while True:
        print("[Agent] Sending heartbeat...")
        heartbeat(AGENT_ID, HUB_URL)
        print("[Agent] Running inference...")
        run_inference()
        time.sleep(10)

if __name__ == "__main__":
    main_loop()
