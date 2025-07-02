from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class NodeStatus(str, Enum):
    """Node status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NodeCapabilities(BaseModel):
    """Node capabilities and specifications."""
    gpu_count: int = 0
    gpu_memory: int = 0  # MB
    cpu_cores: int = 1
    memory: int = 0  # MB
    supported_models: List[str] = Field(default_factory=list)
    max_concurrent_tasks: int = 1

class Node(BaseModel):
    """Node model representing a compute node in the system."""
    id: str = Field(..., description="Unique node identifier")
    status: NodeStatus = NodeStatus.OFFLINE
    capabilities: Optional[NodeCapabilities] = None
    last_heartbeat: Optional[datetime] = None
    registered_at: Optional[datetime] = None
    host: Optional[str] = None
    port: Optional[int] = None
    version: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_load: float = 0.0  # 0.0 to 1.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class TaskInput(BaseModel):
    """Task input data structure."""
    prompt: str = Field(..., description="Input prompt for the model")
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    
class TaskResult(BaseModel):
    """Task result data structure."""
    output: Optional[str] = None
    tokens_generated: Optional[int] = None
    processing_time: Optional[float] = None
    model_used: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Task(BaseModel):
    """Task model representing a computation task."""
    id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = TaskStatus.PENDING
    model: str = Field(..., description="Model to use for processing")
    input_data: TaskInput
    result: Optional[TaskResult] = None
    node_id: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=10, description="Task priority (1-10)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class NodeRegistrationRequest(BaseModel):
    """Request model for node registration."""
    id: str
    capabilities: Optional[NodeCapabilities] = None
    host: Optional[str] = None
    port: Optional[int] = None
    version: Optional[str] = None

class NodeHeartbeatRequest(BaseModel):
    """Request model for node heartbeat."""
    id: str
    current_load: Optional[float] = None
    active_tasks: Optional[int] = None

class TaskCreationRequest(BaseModel):
    """Request model for task creation."""
    model: str
    input_data: TaskInput
    priority: int = Field(default=1, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)

class TaskUpdateRequest(BaseModel):
    """Request model for task status updates."""
    status: TaskStatus
    result: Optional[TaskResult] = None
    error: Optional[str] = None

class SystemStats(BaseModel):
    """System statistics model."""
    nodes: Dict[str, int]  # {"total": x, "online": y, "offline": z}
    tasks: Dict[str, int]  # {"pending": x, "running": y, etc.}
    uptime: Optional[float] = None
    version: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
