from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# AI Workforce - Agent types (business-focused)
AgentType = Literal[
    "general", "finance", "procurement", "project", "executive",
]

# AI Workforce - Tool types
ToolType = Literal[
    "api_call", "database_query", "file_operation", "web_search",
    "data_transformation", "notification", "custom",
]

# AI Workforce - Execution status
ExecutionStatus = Literal["pending", "running", "completed", "failed", "cancelled"]

# AI Workforce - LLM providers
LLMProvider = Literal["openai", "anthropic", "azure", "local", "custom"]


class AgentConfig(BaseModel):
    """Configuration for an AI agent"""
    system_prompt: str = Field(default="", max_length=5000)
    max_tokens: int = Field(default=4096, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools_enabled: list[str] = Field(default_factory=list)
    memory_enabled: bool = True
    max_iterations: int = Field(default=10, ge=1, le=50)
    custom_params: dict[str, Any] = Field(default_factory=dict)


class AgentDefinition(BaseModel):
    """Definition for creating/updating an AI agent"""
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    agent_type: AgentType
    enabled: bool = True
    config: AgentConfig = Field(default_factory=AgentConfig)
    tools: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Response model for AI agents"""
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None = None
    agent_type: AgentType
    enabled: bool
    config: AgentConfig
    tools: list[str] = Field(default_factory=list)
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class AgentSummary(BaseModel):
    """Summary model for AI agents"""
    id: UUID
    code: str
    name: str
    agent_type: AgentType
    enabled: bool
    created_at: Any

    model_config = {"from_attributes": True}


class ToolConfig(BaseModel):
    """Configuration for a tool"""
    endpoint: str | None = None
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    query_template: str | None = None
    body_template: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=3, ge=0, le=5)
    custom_params: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definition for creating/updating a tool"""
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    tool_type: ToolType
    enabled: bool = True
    config: ToolConfig = Field(default_factory=ToolConfig)


class ToolResponse(BaseModel):
    """Response model for tools"""
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None = None
    tool_type: ToolType
    enabled: bool
    config: ToolConfig
    created_at: Any

    model_config = {"from_attributes": True}


class ToolSummary(BaseModel):
    """Summary model for tools"""
    id: UUID
    code: str
    name: str
    tool_type: ToolType
    enabled: bool

    model_config = {"from_attributes": True}


class AgentExecutionRequest(BaseModel):
    """Request to execute an agent"""
    agent_code: str = Field(min_length=1, max_length=100)
    input_data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    action: str | None = Field(default=None, max_length=100, description="Override action descriptor for governance checks (overrides service-level action derivation). If omitted, defaults to 'run_agent'.")


class AgentExecutionResponse(BaseModel):
    """Response from agent execution"""
    id: UUID
    agent_code: str
    status: ExecutionStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int | None = None
    created_at: Any

    model_config = {"from_attributes": True}


class LLMConfigDefinition(BaseModel):
    """Definition for LLM configuration"""
    provider: LLMProvider
    model: str = Field(min_length=1, max_length=100)
    api_key: str | None = None
    base_url: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class LLMConfigResponse(BaseModel):
    """Response model for LLM configuration"""
    id: UUID
    tenant_id: UUID
    provider: LLMProvider
    model: str
    base_url: str | None = None
    is_default: bool
    created_at: Any

    model_config = {"from_attributes": True}
