import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from exo_agent.agent import main_loop
from exo_agent.utils import register_agent, heartbeat
from exo_agent.executor import run_inference
from exo_agent.config import AGENT_ID, HUB_URL

class TestAgentUtils:
    """Test agent utility functions."""
    
    @patch('exo_agent.utils.requests.post')
    def test_register_agent_success(self, mock_post):
        """Test successful agent registration."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = register_agent("test-agent", "http://localhost:8000")
        
        assert result is True
        mock_post.assert_called_once_with(
            "http://localhost:8000/nodes/register",
            json={"id": "test-agent"},
            timeout=10
        )
    
    @patch('exo_agent.utils.requests.post')
    def test_register_agent_failure(self, mock_post):
        """Test failed agent registration."""
        mock_post.side_effect = Exception("Connection error")
        
        result = register_agent("test-agent", "http://localhost:8000")
        
        assert result is False
    
    @patch('exo_agent.utils.requests.post')
    def test_heartbeat_success(self, mock_post):
        """Test successful heartbeat."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = heartbeat("test-agent", "http://localhost:8000")
        
        assert result is True
        mock_post.assert_called_once_with(
            "http://localhost:8000/nodes/heartbeat",
            json={"id": "test-agent"},
            timeout=5
        )

def test_run_inference():
    """Test inference execution (placeholder implementation)."""
    # Should not raise exception
    run_inference()
