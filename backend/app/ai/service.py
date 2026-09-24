import json
import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import AIAgent, AIAgentExecution, AILLMConfig
from .schemas import AgentConfig, ToolConfig

logger = logging.getLogger("2to-eos.ai")


# ---------------------------------------------------------------------------
# AI Workforce - Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registry for AI tools with permission checking."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._configs: dict[str, ToolConfig] = {}
        self._permissions: dict[str, dict] = {}

    def register(
        self,
        code: str,
        handler: Callable,
        config: ToolConfig | None = None,
        permissions: dict | None = None,
    ) -> None:
        self._handlers[code] = handler
        if config:
            self._configs[code] = config
        if permissions:
            self._permissions[code] = permissions

    def unregister(self, code: str) -> bool:
        if code in self._handlers:
            del self._handlers[code]
            self._configs.pop(code, None)
            self._permissions.pop(code, None)
            return True
        return False

    def get_handler(self, code: str) -> Callable | None:
        return self._handlers.get(code)

    def get_config(self, code: str) -> ToolConfig | None:
        return self._configs.get(code)

    def list_tools(self) -> list[str]:
        return list(self._handlers.keys())

    def check_permission(self, tool_code: str, agent_type: str) -> bool:
        perms = self._permissions.get(tool_code)
        if not perms:
            return True
        allowed_agents = perms.get("allowed_agents")
        if allowed_agents and agent_type not in allowed_agents:
            return False
        return True

    def execute(self, code: str, params: dict[str, Any], context: dict[str, Any]) -> Any:
        handler = self._handlers.get(code)
        if not handler:
            raise ValueError(f"Tool not found: {code}")

        try:
            return handler(params, context)
        except Exception:
            logger.exception("Tool execution failed: %s", code)
            raise


# Global tool registry
tool_registry = ToolRegistry()


def _register_builtin_tools():
    """Register all built-in business tools."""
    from .tools.business_tools import BUILTIN_TOOLS

    tool_permissions = {
        "search_records": {"allowed_agents": None},
        "aggregate_records": {"allowed_agents": None},
        "get_financial_summary": {"allowed_agents": ["finance", "executive"]},
        "get_workflow_status": {"allowed_agents": ["executive"]},
        "get_recent_events": {"allowed_agents": ["executive"]},
        "get_project_health": {"allowed_agents": ["project", "executive"]},
        "get_procurement_analysis": {"allowed_agents": ["procurement", "executive"]},
    }

    for code, handler in BUILTIN_TOOLS.items():
        tool_registry.register(
            code,
            handler,
            permissions=tool_permissions.get(code),
        )
    logger.info("Registered %d built-in AI tools", len(BUILTIN_TOOLS))


_register_builtin_tools()


# ---------------------------------------------------------------------------
# AI Workforce - LLM Client (via clients module)
# ---------------------------------------------------------------------------

def get_llm_client(provider: str, config: dict[str, Any]):
    from .llm.clients import get_llm_client as _get_llm_client
    return _get_llm_client(provider, config)


# ---------------------------------------------------------------------------
# AI Workforce - Agent Base
# ---------------------------------------------------------------------------

class BaseAgent:
    """Base class for AI agents."""

    def __init__(
        self,
        code: str,
        name: str,
        config: AgentConfig,
        tools: list[str] | None = None,
    ):
        self.code = code
        self.name = name
        self.config = config
        self.tools = tools or []
        self.llm_client = None

    def set_llm_client(self, client) -> None:
        self.llm_client = client

    def run(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        return self.llm_client.generate(messages, temperature=self.config.temperature)

    def _execute_tool(self, tool_code: str, params: dict[str, Any], context: dict[str, Any]) -> Any:
        return tool_registry.execute(tool_code, params, context)

    def _has_tool(self, tool_code: str) -> bool:
        return tool_code in self.tools or tool_registry.get_handler(tool_code) is not None


# ---------------------------------------------------------------------------
# AI Workforce - Business Agents (loaded from agents module)
# ---------------------------------------------------------------------------

from .agents.business_agents import BUSINESS_AGENT_CLASSES

AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "general": BaseAgent,
    **BUSINESS_AGENT_CLASSES,
}


def create_agent(
    code: str,
    name: str,
    agent_type: str,
    config: AgentConfig,
    tools: list[str] | None = None,
) -> BaseAgent:
    """Create an agent instance."""
    agent_class = AGENT_CLASSES.get(agent_type, BaseAgent)
    return agent_class(code=code, name=name, config=config, tools=tools)


# ---------------------------------------------------------------------------
# AI Workforce - Service
# ---------------------------------------------------------------------------

class AIService:
    """AI Workforce service"""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def get_agent(self, code: str) -> AIAgent | None:
        """Get agent by code"""
        return self.db.scalar(
            select(AIAgent).where(
                AIAgent.tenant_id == self.tenant_id,
                AIAgent.code == code,
            )
        )

    def list_agents(self) -> list[AIAgent]:
        """List all agents"""
        return list(self.db.scalars(
            select(AIAgent).where(AIAgent.tenant_id == self.tenant_id)
        ).all())

    def execute_agent(
        self,
        agent_code: str,
        input_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an agent"""
        agent_model = self.get_agent(agent_code)
        if not agent_model:
            raise ValueError(f"Agent not found: {agent_code}")

        if not agent_model.enabled:
            raise ValueError(f"Agent is disabled: {agent_code}")

        # Parse config
        config_data = json.loads(agent_model.config_json)
        config = AgentConfig(**config_data)

        # Parse tools
        tools = json.loads(agent_model.tools_json) if agent_model.tools_json else []

        # Create agent instance
        agent = create_agent(
            code=agent_model.code,
            name=agent_model.name,
            agent_type=agent_model.agent_type,
            config=config,
            tools=tools,
        )

        # Set up LLM client
        llm_config = self._get_default_llm_config()
        if llm_config:
            provider = llm_config.provider
            client_config = json.loads(llm_config.config_json) if llm_config.config_json else {}
            client_config["model"] = llm_config.model
            agent.set_llm_client(get_llm_client(provider, client_config))

        # Execute
        start_time = time.time()
        execution_id = None

        try:
            # Create execution record
            execution = AIAgentExecution(
                tenant_id=self.tenant_id,
                agent_id=agent_model.id,
                agent_code=agent_code,
                input_json=json.dumps(input_data),
                status="running",
            )
            self.db.add(execution)
            self.db.flush()
            execution_id = execution.id

            # Run agent with full context
            agent_context = {
                **(context or {}),
                "db": self.db,
                "tenant_id": str(self.tenant_id),
            }
            result = agent.run(input_data, agent_context)

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Update execution
            execution.status = "completed"
            execution.output_json = json.dumps(result)
            execution.execution_time_ms = execution_time_ms

            # Audit
            audit_record(
                self.db,
                tenant_id=self.tenant_id,
                actor_id=None,
                action="ai.agent.executed",
                resource_type="ai_agent",
                resource_id=agent_model.id,
                metadata={
                    "agent_code": agent_code,
                    "status": "completed",
                    "execution_time_ms": execution_time_ms,
                },
            )

            self.db.commit()

            return {
                "id": str(execution_id),
                "agent_code": agent_code,
                "status": "completed",
                "output": result,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            if execution_id:
                execution = self.db.get(AIAgentExecution, execution_id)
                if execution:
                    execution.status = "failed"
                    execution.error_message = str(e)
                    execution.execution_time_ms = execution_time_ms

            self.db.commit()

            return {
                "id": str(execution_id) if execution_id else None,
                "agent_code": agent_code,
                "status": "failed",
                "error": str(e),
                "execution_time_ms": execution_time_ms,
            }

    def _get_default_llm_config(self) -> AILLMConfig | None:
        """Get default LLM configuration"""
        return self.db.scalar(
            select(AILLMConfig).where(
                AILLMConfig.tenant_id == self.tenant_id,
                AILLMConfig.is_default.is_(True),
            )
        )
