from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROLES = {"admin", "member"}


class TransitionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_state: str = Field(min_length=1, max_length=80)
    to_state: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=100)
    roles: list[str] = Field(min_length=1, max_length=5)
    requires_approval: bool = True

    @model_validator(mode="after")
    def validate_roles(self) -> "TransitionDefinition":
        if not set(self.roles).issubset(ROLES) or len(set(self.roles)) != len(self.roles):
            raise ValueError("roles must contain unique admin/member values")
        return self


class WorkflowDefinitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    states: list[str] = Field(min_length=1, max_length=50)
    initial_state: str = Field(min_length=1, max_length=80)
    transitions: list[TransitionDefinition] = Field(min_length=1, max_length=100)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_graph(self) -> "WorkflowDefinitionCreate":
        if len(set(self.states)) != len(self.states):
            raise ValueError("states must be unique")
        if self.initial_state not in self.states:
            raise ValueError("initial_state must be one of states")
        seen: set[tuple[str, str]] = set()
        for transition in self.transitions:
            if transition.from_state not in self.states or transition.to_state not in self.states:
                raise ValueError("transition states must be declared in states")
            key = (transition.from_state, transition.action)
            if key in seen:
                raise ValueError("each from_state/action pair must be unique")
            seen.add(key)
        return self


class WorkflowDefinitionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    version: int
    initial_state: str
    definition: dict
    is_active: bool


class WorkflowInstanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_code: str = Field(min_length=1, max_length=100)
    reference_type: str = Field(min_length=1, max_length=100)
    reference_id: UUID


class WorkflowInstanceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    workflow_code: str
    workflow_version: int
    reference_type: str
    reference_id: UUID
    current_state: str
    status: str


class WorkflowTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=100)


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool


class ApprovalTaskResponse(BaseModel):
    id: UUID
    workflow_instance_id: UUID
    action: str
    from_state: str
    to_state: str
    status: str
    requested_by: UUID
    decided_by: UUID | None
