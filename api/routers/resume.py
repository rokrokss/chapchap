import os
from fastapi import APIRouter, Request, File, UploadFile, BackgroundTasks
from langchain_community.document_loaders import PyMuPDFLoader
import structlog
from tempfile import NamedTemporaryFile
from core.graph import LangGraphAgent, Message, MatchJobState
from typing import List, Any
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from core.config import settings

router = APIRouter()


def remove_file(path: str) -> None:
    os.remove(path)


async def extract_named_experiences(
    full_text: str, db_pool: AsyncConnectionPool
) -> List[int]:
    named_company_experiences = []
    query = """
        SELECT
        company_id,
        company_name,
        ARRAY_AGG(name_variant ORDER BY name_variant) AS name_variants
        FROM (
        SELECT
            c.id AS company_id,
            c.name AS company_name,
            c.name AS name_variant
        FROM chapchap.companies c
        UNION ALL
        SELECT
            c.id AS company_id,
            c.name AS company_name,
            can.alternate_name AS name_variant
        FROM chapchap.companies c
        JOIN chapchap.company_alternate_names can ON c.id = can.company_id
        ) AS sub
        GROUP BY company_id, company_name;
    """
    async with db_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            company_names = await cur.fetchall()

    for company_name_dict in company_names:
        company_id = company_name_dict["company_id"]
        company_name = company_name_dict["company_name"]
        name_variants = company_name_dict["name_variants"]

        if (company_name in full_text) or any(
            name_variant in full_text for name_variant in name_variants
        ):
            named_company_experiences.append(company_id)
            continue
    return named_company_experiences


async def update_agent_state(
    summary: str,
    agent: LangGraphAgent,
    session_id,
) -> None:
    logger = structlog.get_logger("api.resume.update_agent_state")
    summary = [
        line.strip()[1:].strip().replace(" -> ", ", ").strip()
        for line in summary.strip().split("\n")
        if line.strip()
    ]
    await agent.graph.aupdate_state(
        {"configurable": {"thread_id": session_id}},
        {"summary_sentences": summary},
    )
    logger.info("update_agent_state", session_id=session_id)


@router.post("/analyze", response_model=dict)
async def analyze_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    logger = structlog.get_logger("api.resume.analyze")
    session_id = request.cookies.get("session_id")

    logger.info("analyze_resume", session_id=session_id)

    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

        background_tasks.add_task(remove_file, tmp_path)

    loader = PyMuPDFLoader(file_path=tmp_path)
    documents = loader.load()

    full_text = "\n".join(doc.page_content for doc in documents).lower()

    named_company_experiences = await extract_named_experiences(
        full_text, request.app.state.db_pool
    )

    agent: LangGraphAgent = request.app.state.agent

    await agent.clear_chat_history(session_id)

    async def generate_response():
        chunks = []
        async for chunk in agent.stream_resume_summary(
            full_text, named_company_experiences, session_id
        ):
            logger.info("chunk", chunk=chunk)
            if chunk == settings.DONE_TOKEN:
                chunk = ""
                await update_agent_state(
                    "".join(chunks),
                    agent,
                    session_id,
                )
            chunks.append(chunk)
            yield f'{{"chunk": "{chunk}", "session_id": "{session_id}"}}'

    return StreamingResponse(generate_response(), media_type="application/json")


@router.get("/match_job", response_model=List[Any])
async def match_job(request: Request):
    logger = structlog.get_logger("api.resume.match_job")
    session_id = request.cookies.get("session_id")
    agent: LangGraphAgent = request.app.state.agent
    agent_thread_config = {"configurable": {"thread_id": session_id}}
    logger.info("match_job", session_id=session_id)
    state = await agent.graph.ainvoke(None, agent_thread_config)

    return state["reranked_results"]
