import os
from fastapi import APIRouter, Request, File, UploadFile, BackgroundTasks
from langchain_community.document_loaders import PyMuPDFLoader
import structlog
from tempfile import NamedTemporaryFile
from core.graph import LangGraphAgent
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
    summary = [
        line.strip()[1:].strip().replace(" -> ", ", ").strip()
        for line in summary.strip().split("\n")
        if (line.strip() and line.startswith("- "))
    ]
    await agent.graph.aupdate_state(
        {"configurable": {"thread_id": session_id}},
        {"summary_sentences": summary},
    )


@router.post("/analyze", response_model=dict)
async def analyze_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    session_id = request.cookies.get("session_id")

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

    messages = agent.resume_summary_messages(full_text)

    async def generate_response():
        chunks = []
        async for chunk in agent.stream_resume_summary(
            messages, full_text, named_company_experiences, session_id
        ):
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


@router.post("/analyze_raw", response_model=dict)
async def analyze_resume_raw(
    request: Request,
):
    session_id = request.cookies.get("session_id")
    body = await request.json()
    raw_resume = body["resume"]

    full_text = raw_resume.lower()

    named_company_experiences = await extract_named_experiences(
        full_text, request.app.state.db_pool
    )

    agent: LangGraphAgent = request.app.state.agent

    await agent.clear_chat_history(session_id)

    messages = agent.resume_summary_messages(full_text)

    async def generate_response():
        chunks = []
        async for chunk in agent.stream_resume_summary(
            messages, full_text, named_company_experiences, session_id
        ):
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
    session_id = request.cookies.get("session_id")
    agent: LangGraphAgent = request.app.state.agent
    agent_thread_config = {"configurable": {"thread_id": session_id}}
    state = await agent.graph.ainvoke(None, agent_thread_config)

    return state["reranked_results"]


@router.get("/generate_cover_letter/{job_id}", response_model=dict)
async def generate_cover_letter(request: Request, job_id: str):
    logger = structlog.get_logger("api.resume.generate_cover_letter")
    session_id = request.cookies.get("session_id")
    agent: LangGraphAgent = request.app.state.agent
    agent_thread_config = {"configurable": {"thread_id": session_id}}
    logger.info("generate_cover_letter", job_id=job_id)

    stateSnapshot = await agent.graph.aget_state(agent_thread_config)
    resume_text = stateSnapshot.values["resume_text"]

    cover_letter_prompt = await agent.get_cover_letter_prompt(resume_text, job_id)

    async def generate_response():
        async for chunk in agent.stream_cover_letter(cover_letter_prompt):
            yield f'{{"chunk": "{chunk}", "session_id": "{session_id}"}}'

    return StreamingResponse(generate_response(), media_type="application/json")
