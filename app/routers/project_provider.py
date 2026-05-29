from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import HttpError
from app.models import ProjectProvider
from app.schemas import Page, ProjectInfo, ProjectProviderRead

router = APIRouter(prefix="/api")


def _to_read(pp: ProjectProvider) -> ProjectProviderRead:
    return ProjectProviderRead.model_validate(
        {
            **{c.name: getattr(pp, c.name) for c in pp.__table__.columns},
            "project": ProjectInfo(
                client_id=pp.client_id,
                is_nda_required=pp.is_nda_required,
                is_coi_required=pp.is_coi_required,
                is_invite_approval_required=pp.is_invite_approval_required,
            ),
        }
    )


async def _list(
    session: AsyncSession, project_id: UUID, provider_id: UUID | None, offset: int, limit: int
) -> Page[ProjectProviderRead]:
    base = select(ProjectProvider).where(ProjectProvider.project_id == project_id)
    if provider_id is not None:
        base = base.where(ProjectProvider.provider_id == provider_id)

    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await session.execute(base.offset(offset).limit(limit))).scalars().all()
    return Page[ProjectProviderRead](
        count=total, items=[_to_read(r) for r in rows], offset=offset, limit=limit
    )


async def _detail(session: AsyncSession, project_id: UUID, provider_id: UUID) -> ProjectProviderRead:
    pp = (
        await session.execute(
            select(ProjectProvider).where(
                ProjectProvider.project_id == project_id,
                ProjectProvider.provider_id == provider_id,
            )
        )
    ).scalar_one_or_none()
    if pp is None:
        raise HttpError(404, "project_provider not found")
    return _to_read(pp)


@router.get("/public/v1/project_provider", response_model=Page[ProjectProviderRead])
async def list_public(
    project_id: UUID = Query(...),
    provider_id: UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> Page[ProjectProviderRead]:
    return await _list(session, project_id, provider_id, offset, limit)


@router.get("/private/v1/project_provider", response_model=Page[ProjectProviderRead])
async def list_private(
    project_id: UUID = Query(...),
    provider_id: UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> Page[ProjectProviderRead]:
    return await _list(session, project_id, provider_id, offset, limit)


@router.get(
    "/public/v1/project_provider/project/{project_id}/provider/{provider_id}",
    response_model=ProjectProviderRead,
)
async def get_public(
    project_id: UUID,
    provider_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectProviderRead:
    return await _detail(session, project_id, provider_id)


@router.get(
    "/private/v1/project_provider/project/{project_id}/provider/{provider_id}",
    response_model=ProjectProviderRead,
)
async def get_private(
    project_id: UUID,
    provider_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectProviderRead:
    return await _detail(session, project_id, provider_id)
