import os
from fastapi import APIRouter, Request, File, UploadFile, BackgroundTasks
from langchain_community.document_loaders import PyMuPDFLoader
import structlog
from tempfile import NamedTemporaryFile
from core.graph import LangGraphAgent, Message, MatchJobState, DONE_TOKEN
from typing import List, Any
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from collections import defaultdict

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
    full_text: str,
    named_company_experiences: List[int],
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
    match_job_state = MatchJobState(
        messages=[],
        resume_text=full_text,
        named_company_experiences=named_company_experiences,
        summary_sentences=summary,
        sentence_embeddings=[],
        avg_embedding=[],
        retrieved_matches=[],
    )
    await agent.graph.aupdate_state(
        {"configurable": {"thread_id": session_id}},
        match_job_state,
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

    messages: List[Message] = [
        Message(
            role="system",
            content=f"""
아래 이력서를 읽고 지원자의 경력의 순서를 명시하고, 지원자가 가진 능력을 한 줄 씩 적어주세요.
경력 기준 가장 강한 능력으로 보이는 것을 먼저 적어주세요.

출력 형식:
- "->"로 구분된 학력/경력
- 능력 1
- 능력 2
- 능력 3
...

출력 예시:
- 카이스트 학부 -> 크래프톤 (프론트엔드 엔지니어) -> 토스 (DevOps 엔지니어)
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
        chunks = []
        async for chunk in agent.stream_resume_summary(messages, session_id):
            logger.info("chunk", chunk=chunk)
            if chunk == DONE_TOKEN:
                chunk = ""
                await update_agent_state(
                    full_text,
                    named_company_experiences,
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

    job_id_distance_map = {}
    for match in state["retrieved_matches"]:
        job_id_distance_map[match["job_id"]] = match["distance"]

    async with request.app.state.db_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            job_ids = list(job_id_distance_map.keys())
            await cur.execute(
                """
                SELECT
                    j.*,
                    c.name AS company_name,
                    ac.name AS affiliate_company_name,
                    ARRAY_REMOVE(ARRAY_AGG(t.name), NULL) AS tags
                FROM job_info j
                JOIN companies c ON j.company_id = c.id 
                JOIN affiliate_companies ac ON j.affiliate_company_id = ac.id
                LEFT JOIN job_tags jt ON j.id = jt.job_id
                LEFT JOIN tags t ON jt.tag_id = t.id
                WHERE j.id = ANY(%s)
                GROUP BY j.id, c.name, ac.name
                """,
                (job_ids,),
            )
            job_rows = await cur.fetchall()

            await cur.execute(
                """
                    SELECT job_id, type, sentence_index, sentence
                    FROM chapchap.job_qualification_sentences
                    WHERE type != 'title'
                    ORDER BY job_id, type, sentence_index
                """
            )
            sentence_rows = await cur.fetchall()

    qualifications_map = defaultdict(lambda: {"required": [], "preferred": []})
    for row in sentence_rows:
        qualifications_map[row["job_id"]][row["type"]].append(row["sentence"])

    results = []
    for job in job_rows:
        job_dict = dict(job)
        job_id = job_dict["id"]
        job_dict["qualifications"] = qualifications_map[job_id]["required"]
        job_dict["preferred_qualifications"] = qualifications_map[job_id]["preferred"]
        job_dict["cosine_similarity"] = 1 - job_id_distance_map[job_id]
        results.append(job_dict)

    results.sort(key=lambda x: x["cosine_similarity"], reverse=True)

    return results
