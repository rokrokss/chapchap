from fastapi import FastAPI
from typing import List
import asyncpg
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "54322"),
    "schema": os.getenv("DB_SCHEMA", "chapssal"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.create_pool(
        database=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        server_settings={"search_path": DB_CONFIG["schema"]},
    )
    yield
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)


@app.get("/job_info", response_model=List[dict])
async def get_job_info():
    query = "SELECT * FROM job_info;"
    print(app.state)
    async with app.state.db.acquire() as connection:
        rows = await connection.fetch(query)
    return [dict(row) for row in rows]
