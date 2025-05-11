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
from core.prompts import rerank_job_prompt, cover_letter_prompt, resume_summary_prompt


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

    def resume_summary_messages(self, resume_text):
        messages: List[Message] = [
            Message(
                role="system",
                content=resume_summary_prompt(),
            ),
            Message(role="user", content=resume_text),
        ]

        return messages

    async def stream_resume_summary(
        self,
        messages: List[Message],
        resume_text: str,
        named_company_experiences: list[int],
        session_id: str,
    ) -> AsyncGenerator[str, None]:

        try:
            async for token, _ in self.graph.astream(
                {
                    "messages": [message.model_dump() for message in messages],
                    "resume_text": resume_text,
                    "named_company_experiences": named_company_experiences,
                },
                {"configurable": {"thread_id": session_id}},
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
                        FROM chapchap.job_embeddings
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
                    FROM chapchap.job_info j
                    JOIN chapchap.companies c ON j.company_id = c.id 
                    JOIN chapchap.affiliate_companies ac ON j.affiliate_company_id = ac.id
                    LEFT JOIN chapchap.job_tags jt ON j.id = jt.job_id
                    LEFT JOIN chapchap.tags t ON jt.tag_id = t.id
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

        named_company_experiences = state["named_company_experiences"]
        results = []
        for job in job_rows:
            job_dict = dict(job)
            job_id = job_dict["id"]
            if job_id in named_company_experiences:
                continue
            job_dict["qualifications"] = qualifications_map[job_id]["required"]
            job_dict["preferred_qualifications"] = qualifications_map[job_id][
                "preferred"
            ]
            job_dict["cosine_similarity"] = 1 - job_id_distance_map[job_id]
            results.append(job_dict)

        results.sort(key=lambda x: x["cosine_similarity"], reverse=True)

        return {"retrieved_jobs": results}

    async def _rerank_matches(self, state: MatchJobState) -> dict:
        prompt = rerank_job_prompt(state["resume_text"], state["retrieved_jobs"])
        messages = [HumanMessage(content=prompt)]
        structured_llm = self.model.with_structured_output(RerankedJobList)
        rerank_output = await structured_llm.ainvoke(messages)

        result = []
        for job in rerank_output.results:
            job_info = state["retrieved_jobs"][job.job_idx]
            job_info["reason"] = job.reason
            job_info["rank_title"] = job.job_title
            result.append(job_info)

        return {"reranked_results": result}

    # coverletter

    async def get_cover_letter_prompt(self, resume_text: str, job_id: str) -> str:
        async with self._db_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                        SELECT
                            j.*,
                            c.name AS company_name,
                            ac.name AS affiliate_company_name
                        FROM chapchap.job_info j
                        JOIN chapchap.companies c ON j.company_id = c.id 
                        JOIN chapchap.affiliate_companies ac ON j.affiliate_company_id = ac.id
                        WHERE j.id = %s
                    """,
                    (job_id,),
                )
                job_row = await cur.fetchone()

                await cur.execute(
                    """
                        SELECT job_id, type, sentence_index, sentence
                        FROM chapchap.job_qualification_sentences
                        WHERE type != 'title' AND job_id = %s
                        ORDER BY job_id, type, sentence_index
                    """,
                    (job_id,),
                )
                sentence_rows = await cur.fetchall()

        qualifications_map = defaultdict(lambda: {"required": [], "preferred": []})
        for row in sentence_rows:
            qualifications_map[row["job_id"]][row["type"]].append(row["sentence"])

        job_dict = dict(job_row)
        job_dict["qualifications"] = qualifications_map[job_id]["required"]
        job_dict["preferred_qualifications"] = qualifications_map[job_id]["preferred"]

        return cover_letter_prompt(resume_text, job_dict)

    async def stream_cover_letter(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            async for chunk in self.model.astream(prompt):
                try:
                    yield chunk.content
                except Exception as e:
                    self.logger.error("error_processing_token", error=str(e))
                    raise e

        except Exception as e:
            self.logger.error("error_stream", error=str(e))
            raise e

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
            max_lifetime=60,
            kwargs={
                "autocommit": True,
                "prepare_threshold": None,
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
                        DELETE FROM chapchap.{table}
                        WHERE thread_id = %s
                        """,
                        (session_id,),
                    )
                    self.logger.info(
                        f"Cleared chapchap.{table} for session {session_id}"
                    )

    async def close(self):
        await self._db_pool.close()
