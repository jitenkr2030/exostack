import requests

def register_agent(agent_id, hub_url):
    requests.post(f"{hub_url}/nodes/register", json={"id": agent_id})

def heartbeat(agent_id, hub_url):
    requests.post(f"{hub_url}/nodes/heartbeat", json={"id": agent_id})
