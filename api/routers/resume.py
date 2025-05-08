import os
from fastapi import APIRouter, Request, File, UploadFile, BackgroundTasks
from langchain_community.document_loaders import PyMuPDFLoader
import structlog
from tempfile import NamedTemporaryFile
from core.langgraph.graph import LangGraphAgent, Message
from typing import List
from fastapi.responses import StreamingResponse

router = APIRouter()


def remove_file(path: str) -> None:
    os.remove(path)


@router.post("/analyze", response_model=dict)
async def analyze_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    logger = structlog.get_logger("api.resume")
    session_id = request.cookies.get("session_id")

    logger.info("analyze_resume", session_id=session_id)

    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

        background_tasks.add_task(remove_file, tmp_path)

    loader = PyMuPDFLoader(file_path=tmp_path)
    documents = loader.load()

    full_text = "\n".join(doc.page_content for doc in documents)

    agent: LangGraphAgent = request.app.state.agent

    messages: List[Message] = [
        Message(
            role="system",
            content=f"""
아래 이력서를 읽고 지원자가 가진 능력을 한 줄 씩 적어주세요.
경력 기준 가장 강한 능력으로 보이는 것을 먼저 적어주세요.

출력 형식:
- 능력 1
- 능력 2
- 능력 3
...

출력 예시:
- Java 및 Spring Framework 활용 개발 경험 및 AWS 환경 경험
- React, Vue 등 최신 프론트엔드 프레임워크 및 유형 컴포넌트 UI 설계 경험
- 광고 및 이커머스 도메인 경험
- MLOps와 LLMOps 파이프라인 구현 및 관리
- Kubernetes 등 컨테이너 오케스트레이션 시스템 활용 운영 경험
- 대화형 AI, 음성인식, NLP 등 AI/ML 관련 솔루션 실무 경험
            """,
        ),
        Message(role="user", content=full_text),
    ]

    await agent.clear_chat_history(session_id)

    async def generate_response():
        async for chunk in agent.get_stream_response(messages, session_id):

            yield f'{{"chunk": "{chunk}", "session_id": "{session_id}"}}'

    return StreamingResponse(generate_response(), media_type="application/json")
