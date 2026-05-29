from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Sequence, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ProjectProviderBatch(Base):
    __tablename__ = "project_provider_batch"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    allow_auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectProvider(Base):
    __tablename__ = "project_provider"
    __table_args__ = (UniqueConstraint("project_id", "provider_id", name="uq_project_provider"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    provider_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String, nullable=True)

    batch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("project_provider_batch.id"), nullable=True
    )
    account_status: Mapped[str] = mapped_column(String, default="ACTIVE")
    phase: Mapped[str] = mapped_column(String, default="INVITED")
    previous_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, default="INVITE_STARTED")
    previous_state: Mapped[str | None] = mapped_column(String, nullable=True)

    invited_via_one_click_invite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_waiting_for_invite_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_waiting_for_nda: Mapped[bool] = mapped_column(Boolean, default=False)
    is_waiting_for_coi: Mapped[bool] = mapped_column(Boolean, default=False)
    is_revealed_to_provider: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    provider_invited: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_invited_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    interested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_phase_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_provider_presence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nda_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    award_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    award_completed_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    proposal_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    decline_feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exclusion_feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    phase_before_decline: Mapped[str | None] = mapped_column(String, nullable=True)
    phase_before_exclusion: Mapped[str | None] = mapped_column(String, nullable=True)

    nda_flow_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    coi_flow_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    invite_approval_flow_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    latest_command_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    client_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    is_nda_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_coi_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_invite_approval_required: Mapped[bool] = mapped_column(Boolean, default=False)


_project_provider_command_seq = Sequence("project_provider_command_seq")


class ProjectProviderCommand(Base):
    __tablename__ = "project_provider_command"
    __table_args__ = (
        UniqueConstraint(
            "previous_command_id", name="uq_project_provider_command_previous_command_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    clock: Mapped[int] = mapped_column(
        _project_provider_command_seq, server_default=_project_provider_command_seq.next_value()
    )

    command_type: Mapped[str] = mapped_column(String)
    parent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    previous_command_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    provider_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    project_provider_batch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("project_provider_batch.id"), nullable=True
    )

    provider_name: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    account_status: Mapped[str | None] = mapped_column(String, nullable=True)
    nda_flow_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    coi_flow_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    invite_approval_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    is_waiting_for_nda: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_waiting_for_invite_approval: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latest_provider_presence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_via_one_click_invite: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feedback_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)


class NdaCommand(Base):
    __tablename__ = "nda_command"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))

    nda_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid4)
    command_type: Mapped[str] = mapped_column(String)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    provider_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)

    accepted_file_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    add_coversheet_operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    copy_operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    file_operation_type: Mapped[str | None] = mapped_column(String, nullable=True)
    signable_file_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    selected_file_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    selected_file_type: Mapped[str | None] = mapped_column(String, nullable=True)
    signatory_first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    signatory_last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    signatory_title: Mapped[str | None] = mapped_column(String, nullable=True)
    signatory_legal_entity: Mapped[str | None] = mapped_column(String, nullable=True)
    pending_waive: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    pending_source_file_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    project_provider: Mapped["ProjectProvider | None"] = relationship(
        primaryjoin="and_(NdaCommand.project_id == foreign(ProjectProvider.project_id), "
        "NdaCommand.provider_id == foreign(ProjectProvider.provider_id))",
        viewonly=True,
        uselist=False,
    )
