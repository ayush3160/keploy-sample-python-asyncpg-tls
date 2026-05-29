import asyncio
import logging

from app.db import engine, init_db

log = logging.getLogger("init_schema")
logging.basicConfig(level=logging.INFO)


async def _run() -> None:
    log.info("creating database schema if missing")
    await init_db()
    await engine.dispose()
    log.info("schema ready")


if __name__ == "__main__":
    asyncio.run(_run())
