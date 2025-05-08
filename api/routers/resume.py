import os
from fastapi import APIRouter, Request, File, UploadFile, BackgroundTasks
from langchain_community.document_loaders import PyMuPDFLoader
import structlog
from tempfile import NamedTemporaryFile
from core.langgraph.graph import LangGraphAgent, State

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

    config = {"configurable": {"thread_id": session_id}}

    state: State = {
        "messages": [
            {
                "role": "system",
                "content": "아래 이력서를 요약해줘. 경력, 기술, 역할 중심으로 간단히 써줘.",
            },
            {"role": "user", "content": full_text},
        ]
    }

    result = await agent._graph.ainvoke(state, config)
    summary = result["messages"][-1].content

    return {"summary": summary, "session_id": session_id}
