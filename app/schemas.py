from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ProjectInfo(CamelModel):
    client_id: UUID | None = None
    is_nda_required: bool = False
    is_coi_required: bool = False
    is_invite_approval_required: bool = False


class ProjectProviderRead(CamelModel):
    id: UUID
    account_status: str
    award_completed_at: datetime | None = None
    award_completed_by: UUID | None = None
    batch_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    decline_feedback: dict | None = None
    exclusion_feedback: dict | None = None
    interested_at: datetime | None = None
    invited_via_one_click_invite: bool = False
    is_waiting_for_invite_approval: bool = False
    is_waiting_for_nda: bool = False
    is_waiting_for_coi: bool = False
    is_revealed_to_provider: bool = False
    is_archived: bool = False
    latest_phase_update: datetime | None = None
    latest_provider_presence: datetime | None = None
    nda_completed_at: datetime | None = None
    phase_before_decline: str | None = None
    phase_before_exclusion: str | None = None
    phase: str
    previous_phase: str | None = None
    project_id: UUID
    proposal_submitted: bool = False
    provider_id: UUID
    provider_invited_at: datetime | None = None
    provider_invited_by: UUID | None = None
    provider_invited: bool = False
    provider_name: str | None = None
    workspace_id: UUID | None = None
    state: str
    previous_state: str | None = None
    coi_flow_id: UUID | None = None
    nda_flow_id: UUID | None = None
    invite_approval_flow_id: UUID | None = None
    latest_command_id: UUID | None = None
    project: ProjectInfo


class PageLinks(CamelModel):
    next: str | None = None
    prev: str | None = None


class Page(CamelModel, Generic[T]):
    links: PageLinks | None = None
    count: int
    items: list[T]
    offset: int = 0
    limit: int = 100

    model_config = ConfigDict(
        alias_generator=lambda f: "_links" if f == "links" else to_camel(f),
        populate_by_name=True,
        from_attributes=True,
    )


class BatchProviderInput(CamelModel):
    workspace_id: UUID
    provider_name: str
    provider_id: UUID
    selected_nda_file_id: UUID | None = None
    is_approval_required: bool = False
    approval_id: UUID | None = None


class BatchCreate(CamelModel):
    created_by: UUID
    project_id: UUID
    providers: list[BatchProviderInput]
    allow_auto_approve: bool = False


class BatchRead(CamelModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    project_id: UUID
    provider_ids: list[UUID]
    allow_auto_approve: bool


class ProjectProviderCommandCreate(CamelModel):
    command_type: str
    state: str | None = None
    created_by: UUID
    project_provider_batch_id: UUID | None = None
    nda_flow_id: UUID | None = None
    invite_approval_id: UUID | None = None
    project_id: UUID
    provider_id: UUID
    provider_name: str | None = None
    workspace_id: UUID | None = None
    latest_provider_presence: datetime | None = None
    invited_via_one_click_invite: bool | None = None
    is_waiting_for_invite_approval: bool | None = None
    is_waiting_for_nda: bool | None = None
    feedback: dict | None = None


class ProjectProviderCommandRead(CamelModel):
    id: UUID
    created_at: datetime
    created_by: UUID
    command_type: str
    project_id: UUID
    provider_id: UUID
    workspace_id: UUID | None = None
    provider_name: str | None = None
    state: str | None = None
    project_provider_batch_id: UUID | None = None


class NdaCommandCreate(CamelModel):
    accepted_file_id: UUID | None = None
    add_coversheet_operation_id: UUID | None = None
    command_type: str
    copy_operation_id: UUID | None = None
    created_by: UUID
    file_operation_type: str | None = None
    project_id: UUID
    provider_id: UUID
    signable_file_id: UUID | None = None
    selected_file_id: UUID | None = None
    selected_file_type: str | None = None
    signatory_first_name: str | None = None
    signatory_last_name: str | None = None
    signatory_title: str | None = None
    signatory_legal_entity: str | None = None
    pending_waive: bool | None = None
    pending_source_file_id: UUID | None = None


class NdaCommandRead(NdaCommandCreate):
    id: UUID
    nda_id: UUID
    created_at: datetime
    pending_waive: bool = False


class HealthResponse(CamelModel):
    name: str
    ok: bool = True
