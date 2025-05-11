from langchain.chat_models import init_chat_model
from core.config import settings
from typing import Optional, AsyncGenerator, Annotated, Literal
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
import structlog
from typing_extensions import TypedDict
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from typing import List
import numpy as np
from psycopg.rows import dict_row
from collections import defaultdict
from langchain_core.messages import HumanMessage


class JobMatch(TypedDict):
    job_id: int
    distance: float


class RerankedJob(BaseModel):
    job_idx: int
    job_title: str
    reason: str


class RerankedJobList(BaseModel):
    results: List[RerankedJob]


class MatchJobState(TypedDict):
    messages: Annotated[list, add_messages]
    resume_text: str
    named_company_experiences: list[int]
    summary_sentences: list[str]
    sentence_embeddings: list[list[float]]
    avg_embedding: list[float]
    retrieved_jobs: list[dict]
    reranked_results: list[dict]


class Message(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="The role of the message sender"
    )
    content: str = Field(..., description="The content of the message")


class LangGraphAgent:
    def __init__(self):
        self.logger = structlog.stdlib.get_logger("graph")
        self.model = init_chat_model(
            settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
        )
        self.graph: Optional[CompiledStateGraph] = None
        self._db_pool: Optional[AsyncConnectionPool] = None
        self._openai_client = AsyncOpenAI()
        self.logger.info(
            "llm_initialized",
            model=settings.LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    # summary
    async def _resume_summary(self, state: MatchJobState) -> dict:
        return {
            "messages": [await self.model.ainvoke(state["messages"])],
        }

    async def stream_resume_summary(
        self,
        resume_text: str,
        named_company_experiences: list[int],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": session_id}}

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
            Message(role="user", content=resume_text),
        ]

        try:
            async for token, _ in self.graph.astream(
                {
                    "messages": [message.model_dump() for message in messages],
                    "resume_text": resume_text,
                    "named_company_experiences": named_company_experiences,
                },
                config,
                stream_mode="messages",
            ):
                try:
                    yield token.content
                except Exception as e:
                    self.logger.error(
                        "error_processing_token", error=str(e), session_id=session_id
                    )
                    raise e
            yield settings.DONE_TOKEN
        except Exception as e:
            self.logger.error("error_stream", error=str(e), session_id=session_id)
            raise e

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        self.logger.info(f"임베딩 요청 ({len(texts)} 문장)")
        response = await self._openai_client.embeddings.create(
            input=texts, model=settings.OPENAI_EMBEDDING_MODEL
        )
        return [item.embedding for item in response.data]

    # match
    async def _embed_resume(self, state: MatchJobState) -> dict:
        embeddings = await self.get_embeddings(state["summary_sentences"])
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        return {
            "sentence_embeddings": embeddings,
            "avg_embedding": avg_embedding,
        }

    async def _retrieve_matches(self, state: MatchJobState) -> dict:
        avg_embedding = state["avg_embedding"]
        async with self._db_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                        SELECT
                            job_id, embedding <=> %s::vector AS distance
                        FROM job_embeddings
                        ORDER BY distance
                        LIMIT %s
                    """,
                    (avg_embedding, settings.RETRIEVAL_COUNT),
                )
                rows = await cur.fetchall()

            job_id_distance_map = {}
            for match in rows:
                job_id_distance_map[match["job_id"]] = match["distance"]

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
            job_dict["preferred_qualifications"] = qualifications_map[job_id][
                "preferred"
            ]
            job_dict["cosine_similarity"] = 1 - job_id_distance_map[job_id]
            results.append(job_dict)

        results.sort(key=lambda x: x["cosine_similarity"], reverse=True)

        return {"retrieved_jobs": results}

    async def _rerank_matches(self, state: MatchJobState) -> dict:
        retrieved_jobs = state["retrieved_jobs"]
        resume_text = state["resume_text"]
        job_list = "\n\n".join(
            [
                f"공고번호 {i}. {job['job_title']} ({job['company_name']})\n"
                f"  - 팀 소개: {job['team_info']}\n"
                f"  - 담당업무:\n    " + "\n    ".join(job["responsibilities"]) + "\n"
                f"  - 지원자격:\n    " + "\n    ".join(job["qualifications"]) + "\n"
                f"  - 우대사항:\n    " + "\n    ".join(job["preferred_qualifications"])
                for i, job in enumerate(retrieved_jobs)
            ]
        )
        prompt = f"""
다음은 당신이 가진 채용공고의 리스트입니다.
당신은 이 채용공고 중 지원자가 적합한 {settings.RERANK_COUNT}개의 공고를 선별하고 적합한 순으로 정렬하고 설명을 첨부해야 합니다.
적합한 이유는 100자 이내로 명시해야 합니다.
지원자의 이름은 언급하지 않고 지원자라고 표현해야 합니다.

이력서는 다음과 같습니다.
===이력서 (정제되지 않은 텍스트)
{resume_text}


===채용공고 리스트
{job_list}


===출력 형식
"공고번호" (key: job_idx)
"공고이름" (key: job_title)
"적합한 이유" (key: reason)

{{ "results": [{{ "job_idx": "...", "job_title": "...", "reason": "..." }}, ...] }}
"""
        messages = [HumanMessage(content=prompt)]
        structured_llm = self.model.with_structured_output(RerankedJobList)
        rerank_output = await structured_llm.ainvoke(messages)
        self.logger.info(f"Reranked output: {rerank_output}")

        result = []
        for job in rerank_output.results:
            job_info = retrieved_jobs[job.job_idx]
            job_info["reason"] = job.reason
            job_info["rank_title"] = job.job_title
            result.append(job_info)

        return {"reranked_results": result}

    @classmethod
    async def create(cls) -> "LangGraphAgent":
        agent = cls()
        await agent._get_connection_pool()
        await agent._create_graph()
        return agent

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        self._db_pool = AsyncConnectionPool(
            conninfo=str(settings.POSTGRES_URL),
            open=False,
            max_size=settings.LLM_DB_POOL_SIZE,
            kwargs={
                "autocommit": True,
                "options": f"-c search_path={settings.POSTGRES_SCHEMA}",
            },
        )
        await self._db_pool.open(wait=True)
        return self._db_pool

    async def _create_graph(self):
        checkpointer = AsyncPostgresSaver(self._db_pool)
        await checkpointer.setup()

        graph_builder = StateGraph(MatchJobState)
        graph_builder.add_node("resume_summary", self._resume_summary)
        graph_builder.add_node("embed_resume", self._embed_resume)
        graph_builder.add_node("retrieve_matches", self._retrieve_matches)
        graph_builder.add_node("rerank_matches", self._rerank_matches)
        graph_builder.add_edge("resume_summary", "embed_resume")
        graph_builder.add_edge("embed_resume", "retrieve_matches")
        graph_builder.add_edge("retrieve_matches", "rerank_matches")
        graph_builder.set_entry_point("resume_summary")
        graph_builder.set_finish_point("rerank_matches")

        self.graph = graph_builder.compile(
            checkpointer=checkpointer,
            name="chapchap_graph",
            interrupt_before=["embed_resume"],
        )

    async def clear_chat_history(self, session_id: str) -> None:
        async with self._db_pool.connection() as conn:
            async with conn.cursor() as cur:
                for table in settings.CHECKPOINT_TABLES:
                    await cur.execute(
                        f"""
                        DELETE FROM {table}
                        WHERE thread_id = %s
                        """,
                        (session_id,),
                    )
                    self.logger.info(f"Cleared {table} for session {session_id}")

    async def close(self):
        await self._db_pool.close()
