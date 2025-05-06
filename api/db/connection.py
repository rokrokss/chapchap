import asyncpg
from core.config import settings


async def get_db():
    return await asyncpg.create_pool(
        database=settings.DB_CONFIG["dbname"],
        user=settings.DB_CONFIG["user"],
        password=settings.DB_CONFIG["password"],
        host=settings.DB_CONFIG["host"],
        port=settings.DB_CONFIG["port"],
        server_settings={"search_path": settings.DB_CONFIG["schema"]},
    )
