from __future__ import annotations

import json
from uuid import UUID

import httpx

from eos_v2.domain.ai_composer.entities import ProposalChange
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition


class OpenAICompatibleComposerProvider:
    """Calls an OpenAI-compatible endpoint (including self-hosted Qwen) and accepts JSON only."""

    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def propose(self, prompt: str, tenant_id: UUID) -> tuple[ProposalChange, ...]:
        if not self.base_url or not self.api_key or not self.model:
            raise RuntimeError("AI Composer provider is not configured")
        system = (
            "You are EOS metadata architect. Return JSON only. Never return code. "
            "Propose metadata changes, not database SQL or executable actions. "
            "Schema: {changes:[{rationale:string,entity:{name:string,label:string,fields:[{name:string,field_type:string,required:boolean,unique:boolean}],relationships:[{name:string,target_entity_id:string,required:boolean}]}}]}. "
            "Allowed field_type values: text, integer, decimal, boolean, date, datetime, uuid, json. "
            "Do not invent tenant_id fields; EOS owns tenancy."
        )
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        data = json.loads(content) if isinstance(content, str) else content
        if not isinstance(data, dict) or not isinstance(data.get("changes"), list) or not data["changes"] or len(data["changes"]) > 20:
            raise ValueError("AI provider returned an invalid proposal size or envelope")
        changes: list[ProposalChange] = []
        for item in data["changes"]:
            raw = item["entity"]
            raw_fields = raw.get("fields", [])
            raw_relationships = raw.get("relationships", [])
            if not isinstance(raw_fields, list) or len(raw_fields) > 50 or not isinstance(raw_relationships, list) or len(raw_relationships) > 50:
                raise ValueError("AI provider returned an oversized entity definition")
            fields = tuple(FieldDefinition(
                name=f["name"], field_type=FieldType(f["field_type"]), required=bool(f.get("required")), unique=bool(f.get("unique"))
            ) for f in raw_fields)
            relationships = tuple(RelationshipDefinition(
                name=r["name"], target_entity_id=UUID(r["target_entity_id"]), required=bool(r.get("required"))
            ) for r in raw_relationships)
            entity = EntityDefinition(tenant_id=tenant_id, name=raw["name"], label=raw.get("label", ""), fields=fields, relationships=relationships)
            changes.append(ProposalChange(entity=entity, rationale=item.get("rationale", "AI metadata proposal")))
        return tuple(changes)
