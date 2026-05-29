from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import NdaCommand
from app.schemas import NdaCommandCreate, NdaCommandRead
from app.sns import get_publisher

router = APIRouter(prefix="/api/public/v1")


_COMMAND_TYPE_TO_EVENT = {
    "INITIALIZE": "initialize",
    "SELECT": "select",
    "SET_FILE_OPERATION_ID": "mark_ready_for_signature",
    "MARK_READY_FOR_SIGNATURE": "mark_ready_for_signature",
    "WAIVE": "waive",
}


@router.post("/nda/command", response_model=NdaCommandRead, status_code=status.HTTP_201_CREATED)
async def post_nda_command(
    payload: NdaCommandCreate, session: AsyncSession = Depends(get_session)
) -> NdaCommandRead:
    cmd = NdaCommand(
        id=uuid4(),
        nda_id=uuid4(),
        created_by=payload.created_by,
        command_type=payload.command_type,
        project_id=payload.project_id,
        provider_id=payload.provider_id,
        accepted_file_id=payload.accepted_file_id,
        add_coversheet_operation_id=payload.add_coversheet_operation_id,
        copy_operation_id=payload.copy_operation_id,
        file_operation_type=payload.file_operation_type,
        signable_file_id=payload.signable_file_id,
        selected_file_id=payload.selected_file_id,
        selected_file_type=payload.selected_file_type,
        signatory_first_name=payload.signatory_first_name,
        signatory_last_name=payload.signatory_last_name,
        signatory_title=payload.signatory_title,
        signatory_legal_entity=payload.signatory_legal_entity,
        pending_waive=bool(payload.pending_waive),
        pending_source_file_id=payload.pending_source_file_id,
    )
    session.add(cmd)
    await session.commit()
    await session.refresh(cmd)

    event = _COMMAND_TYPE_TO_EVENT.get(payload.command_type)
    if event:
        publisher = get_publisher()
        publisher.publish(
            media_type=f"application/vnd.globality.pubsub._.created.nda_command.{event}",
            resource_uri=publisher.message_uri("api/private/v1/nda/command", str(cmd.id)),
        )

    return NdaCommandRead(
        id=cmd.id,
        nda_id=cmd.nda_id,
        created_at=cmd.created_at,
        created_by=cmd.created_by,
        command_type=cmd.command_type,
        project_id=cmd.project_id,
        provider_id=cmd.provider_id,
        accepted_file_id=cmd.accepted_file_id,
        add_coversheet_operation_id=cmd.add_coversheet_operation_id,
        copy_operation_id=cmd.copy_operation_id,
        file_operation_type=cmd.file_operation_type,
        signable_file_id=cmd.signable_file_id,
        selected_file_id=cmd.selected_file_id,
        selected_file_type=cmd.selected_file_type,
        signatory_first_name=cmd.signatory_first_name,
        signatory_last_name=cmd.signatory_last_name,
        signatory_title=cmd.signatory_title,
        signatory_legal_entity=cmd.signatory_legal_entity,
        pending_waive=cmd.pending_waive,
        pending_source_file_id=cmd.pending_source_file_id,
    )
