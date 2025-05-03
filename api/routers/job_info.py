from fastapi import APIRouter, Request, Query
from typing import List
from fastapi import Request

router = APIRouter()


@router.get("/job_info/all_active", response_model=List[dict])
async def get_all_active_job_info(
    request: Request,
):
    query = """
        SELECT
        j.*,
        c.name AS company_name,
        ARRAY_REMOVE(ARRAY_AGG(t.name), NULL) AS tags
        FROM job_info j
        JOIN companies c ON j.company_id = c.id
        LEFT JOIN job_tags jt ON j.id = jt.job_id
        LEFT JOIN tags t ON jt.tag_id = t.id
        WHERE j.is_active = true
        GROUP BY j.id, c.name
        ORDER BY j.uploaded_date DESC;
    """
    async with request.app.state.db.acquire() as connection:
        rows = await connection.fetch(query)
    return [dict(row) for row in rows]
