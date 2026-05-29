from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import ProjectProvider, ProjectProviderBatch
from app.schemas import BatchCreate, BatchRead
from app.sns import get_publisher

router = APIRouter(prefix="/api/public/v1")


@router.post("/project_provider_batch", response_model=BatchRead, status_code=status.HTTP_201_CREATED)
async def create_batch(payload: BatchCreate, session: AsyncSession = Depends(get_session)) -> BatchRead:
    batch = ProjectProviderBatch(
        id=uuid4(),
        created_by=payload.created_by,
        project_id=payload.project_id,
        allow_auto_approve=payload.allow_auto_approve,
    )
    session.add(batch)
    await session.flush()  # batch row must exist before project_provider FK references it

    now = datetime.now(timezone.utc)
    for p in payload.providers:
        session.add(
            ProjectProvider(
                project_id=payload.project_id,
                provider_id=p.provider_id,
                workspace_id=p.workspace_id,
                provider_name=p.provider_name,
                batch_id=batch.id,
                nda_flow_id=p.selected_nda_file_id,
                invite_approval_flow_id=p.approval_id,
                is_invite_approval_required=p.is_approval_required,
                provider_invited=True,
                provider_invited_at=now,
                provider_invited_by=payload.created_by,
                latest_phase_update=now,
                phase="INVITED",
                state="INVITE_STARTED",
            )
        )

    await session.commit()
    await session.refresh(batch)

    publisher = get_publisher()
    publisher.publish(
        media_type="application/vnd.globality.pubsub._.created.project_provider_batch",
        resource_uri=publisher.message_uri("api/public/v1/project_provider_batch", str(batch.id)),
    )

    return BatchRead(
        id=batch.id,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        created_by=batch.created_by,
        project_id=batch.project_id,
        provider_ids=[p.provider_id for p in payload.providers],
        allow_auto_approve=batch.allow_auto_approve,
    )
