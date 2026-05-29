from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import HttpError
from app.models import ProjectProvider, ProjectProviderCommand
from app.schemas import ProjectProviderCommandCreate, ProjectProviderCommandRead
from app.sns import get_publisher

router = APIRouter(prefix="/api/public/v1")


_TYPE_TO_PHASE = {
    "INVITE": ("INVITED", "INVITE_STARTED", None),
    "SHOW_INTEREST": ("INTERESTED", "INTERESTED", "provider_showed_interest"),
    "SUBMIT_PROPOSAL": ("PROPOSAL_SUBMITTED", "PROPOSAL_SUBMITTED", "proposal_submitted"),
    "DECLINE": ("DECLINED", "DECLINED", None),
    "EXCLUDE": ("EXCLUDED", "EXCLUDED", None),
    "AWARD": ("AWARDED", "AWARDED", None),
}


@router.post(
    "/project_provider/command",
    response_model=ProjectProviderCommandRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_command(
    payload: ProjectProviderCommandCreate, session: AsyncSession = Depends(get_session)
) -> ProjectProviderCommandRead:
    pp = (
        await session.execute(
            select(ProjectProvider).where(
                ProjectProvider.project_id == payload.project_id,
                ProjectProvider.provider_id == payload.provider_id,
            )
        )
    ).scalar_one_or_none()

    cmd = ProjectProviderCommand(
        id=uuid4(),
        created_by=payload.created_by,
        command_type=payload.command_type,
        project_id=payload.project_id,
        provider_id=payload.provider_id,
        workspace_id=payload.workspace_id,
        project_provider_batch_id=payload.project_provider_batch_id,
        provider_name=payload.provider_name,
        state=payload.state,
        nda_flow_id=payload.nda_flow_id,
        invite_approval_id=payload.invite_approval_id,
        is_waiting_for_nda=payload.is_waiting_for_nda,
        is_waiting_for_invite_approval=payload.is_waiting_for_invite_approval,
        latest_provider_presence=payload.latest_provider_presence,
        invited_via_one_click_invite=payload.invited_via_one_click_invite,
        feedback=payload.feedback,
        previous_command_id=pp.latest_command_id if pp else None,
    )
    session.add(cmd)

    if pp is not None:
        phase, state, event = _TYPE_TO_PHASE.get(payload.command_type, (pp.phase, pp.state, None))
        pp.previous_phase = pp.phase
        pp.previous_state = pp.state
        pp.phase = phase
        pp.state = state
        pp.latest_command_id = cmd.id
        pp.latest_phase_update = datetime.now(timezone.utc)
        if payload.command_type == "SHOW_INTEREST":
            pp.interested_at = datetime.now(timezone.utc)
        if payload.command_type == "SUBMIT_PROPOSAL":
            pp.proposal_submitted = True

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    publisher = get_publisher()
    _, _, event = _TYPE_TO_PHASE.get(payload.command_type, (None, None, None))
    if event:
        publisher.publish(
            media_type=f"application/vnd.globality.pubsub._.created.project_provider_event.{event}",
            resource_uri=publisher.message_uri(
                "api/private/v1/project_provider_command", str(cmd.id)
            ),
        )

    if pp is None:
        raise HttpError(404, "project_provider not found")

    return ProjectProviderCommandRead(
        id=cmd.id,
        created_at=cmd.created_at,
        created_by=cmd.created_by,
        command_type=cmd.command_type,
        project_id=cmd.project_id,
        provider_id=cmd.provider_id,
        workspace_id=cmd.workspace_id,
        provider_name=cmd.provider_name,
        state=cmd.state,
        project_provider_batch_id=cmd.project_provider_batch_id,
    )
