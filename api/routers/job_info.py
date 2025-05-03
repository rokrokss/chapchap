from fastapi import APIRouter, Request, Query
from typing import List
from fastapi import Request

router = APIRouter()


@router.get("/job_info/active", response_model=List[dict])
async def get_active_job_info(
    request: Request, limit: int = Query(20), offset: int = Query(0)
):
    query = f"""
    SELECT * FROM job_info 
    WHERE is_active = true 
    ORDER BY uploaded_date DESC 
    LIMIT {limit} OFFSET {offset};
    """
    async with request.app.state.db.acquire() as connection:
        rows = await connection.fetch(query)
    return [dict(row) for row in rows]


@router.get("/job_info/all_active", response_model=List[dict])
async def get_all_active_job_info(
    request: Request,
):
    query = f"""
    SELECT * FROM job_info 
    WHERE is_active = true 
    ORDER BY uploaded_date DESC;
    """
    async with request.app.state.db.acquire() as connection:
        rows = await connection.fetch(query)
    return [dict(row) for row in rows]
