"""Seed the database with the project_provider rows referenced by the recorded test cases.

UUIDs and field values come straight from the response bodies in
`provider-engagem-provider-engagement-serv-ts-08173f93-217936e4/testset/tests/*.yaml`
so the recorded GETs resolve against a freshly-created DB.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import ProjectProvider, ProjectProviderBatch

log = logging.getLogger("seed")
logging.basicConfig(level=logging.INFO)


CLIENT_ID = UUID("4c5190b9-ffea-4378-938f-3e0e649b8fa9")
PROVIDER_ID = UUID("c1a88792-8ce2-4a88-b619-b924503059d7")


def _utc(year: int, month: int, day: int, hour: int, minute: int, second: int) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


BATCHES = [
    {
        "id": UUID("413a915e-18c3-43eb-96f1-be5a7b11957d"),
        "created_by": UUID("c96a692f-dee0-4593-82a8-589db10d109c"),
        "project_id": UUID("b8f1aced-5640-4409-a6d6-ee2ce3909a68"),
        "allow_auto_approve": False,
    },
    {
        "id": UUID("4c6cef0b-ccc5-4de6-9f2b-3263ca31681e"),
        "created_by": UUID("90ecb6c9-7fb0-4ef1-b4b5-aa8ce14c4ef8"),
        "project_id": UUID("5ad06456-a631-40f0-8d7a-843ae105db89"),
        "allow_auto_approve": False,
    },
]

PROJECT_PROVIDERS = [
    # get-api-private-v1-project-provider-5 / get-api-public-v1-project-provider-10
    {
        "id": UUID("2c49f369-bcea-4fa0-a881-d0032416bc7e"),
        "project_id": UUID("b8f1aced-5640-4409-a6d6-ee2ce3909a68"),
        "provider_id": PROVIDER_ID,
        "workspace_id": UUID("ec7ada5e-755d-46f8-b3f1-c63bf869ea30"),
        "provider_name": "QAAutotest Provider 01",
        "batch_id": UUID("413a915e-18c3-43eb-96f1-be5a7b11957d"),
        "account_status": "ACTIVE",
        "phase": "PROPOSAL_SUBMITTED",
        "state": "PROPOSAL_SUBMITTED",
        "invited_via_one_click_invite": True,
        "is_waiting_for_invite_approval": False,
        "is_waiting_for_nda": False,
        "is_waiting_for_coi": False,
        "is_revealed_to_provider": False,
        "is_archived": False,
        "provider_invited": True,
        "provider_invited_at": _utc(2026, 5, 19, 17, 20, 17),
        "provider_invited_by": UUID("c96a692f-dee0-4593-82a8-589db10d109c"),
        "interested_at": _utc(2026, 5, 19, 17, 20, 48),
        "latest_phase_update": _utc(2026, 5, 19, 17, 21, 4),
        "nda_completed_at": _utc(2026, 5, 19, 17, 20, 17),
        "proposal_submitted": True,
        "nda_flow_id": UUID("94d08ab9-1e93-4e63-ac1a-4bf9459cf12e"),
        "invite_approval_flow_id": UUID("098dd9c5-16c7-40c5-939c-dd14c26bc391"),
        "latest_command_id": UUID("91ce4129-24c1-4a05-814d-d686f07af9e5"),
        "client_id": CLIENT_ID,
        "is_nda_required": True,
        "is_coi_required": False,
        "is_invite_approval_required": False,
    },
    # get-api-private-v1-project-provider-6
    {
        "id": UUID("f6632b1d-b223-4402-adc4-22875dd2a20f"),
        "project_id": UUID("5ad06456-a631-40f0-8d7a-843ae105db89"),
        "provider_id": PROVIDER_ID,
        "workspace_id": UUID("e217c5f0-9cdb-410d-a0d5-65d9af6f5e73"),
        "provider_name": "QAAutotest Provider 01",
        "batch_id": UUID("4c6cef0b-ccc5-4de6-9f2b-3263ca31681e"),
        "account_status": "ACTIVE",
        "phase": "INVITED",
        "state": "INVITED",
        "invited_via_one_click_invite": True,
        "is_waiting_for_nda": True,
        "provider_invited": True,
        "provider_invited_at": _utc(2026, 5, 19, 17, 26, 54),
        "provider_invited_by": UUID("90ecb6c9-7fb0-4ef1-b4b5-aa8ce14c4ef8"),
        "latest_phase_update": _utc(2026, 5, 19, 17, 26, 54),
        "nda_flow_id": UUID("a28369bc-2f97-4906-8dd5-8f5222f01ed5"),
        "invite_approval_flow_id": UUID("a7aa51e4-1fbf-4ad5-8508-00bd76b016cb"),
        "latest_command_id": UUID("bd88e0b9-fa3f-42f4-a726-e76a96c1cc05"),
        "client_id": CLIENT_ID,
        "is_nda_required": True,
        "is_coi_required": False,
        "is_invite_approval_required": False,
    },
]


async def seed() -> None:
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                select(ProjectProvider.id).where(
                    ProjectProvider.id.in_([row["id"] for row in PROJECT_PROVIDERS])
                )
            )
        ).scalars().all()
        if existing:
            log.info("seed: %d rows already present, skipping", len(existing))
            return

        for batch in BATCHES:
            session.add(ProjectProviderBatch(**batch))
        await session.flush()  # batches must exist before project_providers (FK)
        for row in PROJECT_PROVIDERS:
            session.add(ProjectProvider(**row))
        await session.commit()
        log.info("seed: inserted %d batches, %d project_providers", len(BATCHES), len(PROJECT_PROVIDERS))


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    finally:
        asyncio.run(engine.dispose())
