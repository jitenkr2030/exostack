import time
from .config import AGENT_ID, HUB_URL
from .executor import run_inference
from .utils import heartbeat, register_agent

def main_loop():
    register_agent(AGENT_ID, HUB_URL)
    while True:
        heartbeat(AGENT_ID, HUB_URL)
        run_inference()
        time.sleep(10)
