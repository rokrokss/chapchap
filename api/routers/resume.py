from fastapi import APIRouter, Request, File, UploadFile
from typing import List

router = APIRouter()


@router.post("/analyze", response_model=dict)
async def analyze_resume(request: Request, file: UploadFile = File(...)):
    session_id = request.cookies.get("session_id")
    return {"file_name": file.filename, "session_id": session_id}
