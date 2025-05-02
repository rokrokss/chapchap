from fastapi import APIRouter
from typing import List
from fastapi import Request

router = APIRouter()


@router.get("/job_info/active", response_model=List[dict])
async def get_active_job_info(request: Request):
    query = "SELECT * FROM job_info WHERE is_active = true;"
    async with request.app.state.db.acquire() as connection:
        rows = await connection.fetch(query)
    return [dict(row) for row in rows]
