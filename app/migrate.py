import asyncio
from pathlib import Path

from sqlalchemy import inspect, text

from app.database import engine


async def migrate():
    async with engine.begin() as connection:
        columns = await connection.run_sync(lambda sync: inspect(sync).get_columns("progress_record"))
        if "target_snapshot" not in {column["name"] for column in columns}:
            migration = Path(__file__).resolve().parent.parent / "sql" / "issue#17.sql"
            await connection.execute(text(migration.read_text()))
            print("Added progress_record.target_snapshot")
        else:
            print("progress_record.target_snapshot already exists")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
