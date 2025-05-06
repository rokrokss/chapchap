from fastapi import APIRouter
from routers import job_info, resume
from core.config import settings

router = APIRouter(prefix=settings.API_V1_STR)

router.include_router(job_info.router, prefix="/job_info")
router.include_router(resume.router, prefix="/resume")
