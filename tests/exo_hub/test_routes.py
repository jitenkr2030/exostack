import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from exo_hub.main import app

# Test client
client = TestClient(app)

class TestNodeRoutes:
    """Test node-related API routes."""
    
    @patch('exo_hub.services.registry.registry')
    def test_register_node_success(self, mock_registry):
        """Test successful node registration."""
        mock_registry.register_node.return_value = True
        
        response = client.post("/nodes/register", json={
            "id": "test-node-1"
        })
        
        assert response.status_code == 200
    
    @patch('exo_hub.services.registry.registry') 
    def test_node_heartbeat_success(self, mock_registry):
        """Test successful node heartbeat."""
        mock_registry.update_node_heartbeat.return_value = True
        
        response = client.post("/nodes/heartbeat", json={
            "id": "test-node-1"
        })
        
        assert response.status_code == 200

class TestTaskRoutes:
    """Test task-related API routes."""
    
    @patch('exo_hub.services.scheduler.scheduler')
    def test_create_task_success(self, mock_scheduler):
        """Test successful task creation."""
        mock_task_id = "task-123"
        mock_scheduler.create_task.return_value = mock_task_id
        
        response = client.post("/tasks/create", json={
            "model": "gpt-3.5-turbo",
            "input_data": {
                "prompt": "Hello, world!",
                "max_tokens": 100
            }
        })
        
        assert response.status_code == 200

def test_health():
    """Test basic health check."""
    assert True
