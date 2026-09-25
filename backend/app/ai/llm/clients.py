"""LLM Client - real API integration with rule-based fallback."""
import json
import logging
import os
from typing import Any

logger = logging.getLogger("2to-eos.ai.llm")


class LLMClient:
    """Abstract LLM client."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        return False


class OpenAIClient(LLMClient):
    """OpenAI API client."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        if not self.api_key:
            return ""

        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            }

            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.warning("OpenAI API call failed: %s", e)
            return ""


class AnthropicClient(LLMClient):
    """Anthropic API client."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model = config.get("model", "claude-sonnet-4-20250514")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        if not self.api_key:
            return ""

        try:
            import httpx

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }

            system_msg = ""
            user_msgs = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    user_msgs.append(m)

            payload = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "messages": user_msgs,
            }
            if system_msg:
                payload["system"] = system_msg

            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["content"][0]["text"]

        except Exception as e:
            logger.warning("Anthropic API call failed: %s", e)
            return ""


class RuleBasedClient(LLMClient):
    """Rule-based fallback when no LLM API is available."""

    def is_available(self) -> bool:
        return True

    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        if not messages:
            return "No input provided."

        last_msg = messages[-1].get("content", "").lower()

        if any(w in last_msg for w in ["financial", "finance", "account", "ledger", "trial balance"]):
            return "I can see your financial data. For detailed analysis, please use the Finance Agent which can query your accounts, journal entries, and generate reports."
        if any(w in last_msg for w in ["project", "health", "budget"]):
            return "I can analyze your projects. The Project Agent can check budget utilization, risk levels, and project health metrics."
        if any(w in last_msg for w in ["procurement", "supplier", "purchase", "order"]):
            return "I can review your procurement data. The Procurement Agent can analyze pending orders, supplier performance, and spending patterns."
        if any(w in last_msg for w in ["workflow", "approval", "pending"]):
            return "I can check your workflows. The system tracks approval states and can identify bottlenecks."
        if any(w in last_msg for w in ["risk", "problem", "issue", "alert"]):
            return "I can identify risks across your business. The Executive Agent provides a cross-domain risk summary."

        return "I'm ready to help. You can ask about finance, projects, procurement, workflows, or business risks."


def get_llm_client(provider: str, config: dict[str, Any]) -> LLMClient:
    """Get LLM client by provider, with automatic fallback."""
    clients = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
    }

    client_class = clients.get(provider)
    if client_class:
        client = client_class(config)
        if client.is_available():
            logger.info("Using %s LLM client", provider)
            return client
        logger.info("%s API key not found, falling back to rule-based client", provider)

    return RuleBasedClient(config)
