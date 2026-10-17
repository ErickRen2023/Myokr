import asyncio

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.schema import CreateColumn

from app.database import engine
from app.models.base import Base
from app.models.progress_record import ProgressRecord


async def migrate_schema(connection: AsyncConnection) -> bool:
    columns = await connection.run_sync(lambda sync: inspect(sync).get_columns("progress_record"))
    if "target_snapshot" in {column["name"] for column in columns}:
        return False
    column = CreateColumn(ProgressRecord.__table__.c.target_snapshot).compile(dialect=connection.dialect)
    await connection.execute(text(f"ALTER TABLE progress_record ADD COLUMN {column}"))
    return True


async def migrate():
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            added = await migrate_schema(connection)
        print("Added progress_record.target_snapshot" if added else "progress_record.target_snapshot already exists")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
